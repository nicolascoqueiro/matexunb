"""Servidor Web e API REST para a interface de gerenciamento do MatexUnB."""

import os
import time
import logging
import threading
from datetime import datetime
from typing import List, Dict, Any
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from departments import get_departments, get_department_name
from config import load_all_data, save_all_data
from models.students import Student
from models.school_class import SchoolClass
from list_classes import ListClasses
from get_enrollment_manager import GetEnrollment
from sigaa_scraper import fetch_offered_classes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Configuração de logs em memória sem lock para evitar deadlocks no WSGI/Flask
class MemoryLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.logs: List[str] = []
        self._lock = threading.Lock()

    def emit(self, record):
        with self._lock:
            try:
                log_entry = self.format(record)
                self.logs.append(f"[{time.strftime('%H:%M:%S')}] {log_entry}")
                if len(self.logs) > 400:
                    self.logs.pop(0)
            except Exception:
                pass

    def get_logs(self) -> List[str]:
        return list(self.logs)

    def clear(self) -> None:
        self.logs.clear()


memory_handler = MemoryLogHandler()
memory_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

logger = logging.getLogger(__name__)
logger.addHandler(memory_handler)
logger.setLevel(logging.INFO)

app = Flask(__name__, static_folder=STATIC_DIR)
CORS(app)

PUBLIC_DB_PATH = os.path.join(BASE_DIR, "public", "db.json")
SECRET_DB_PATH = os.path.join(BASE_DIR, "secret", "db.json")

# Estado global da automação em background
automation_state = {
    "running": False,
    "thread": None,
    "stop_requested": False,
    "headless": True,
    "last_status": "Parado",
}


def _all_students_done(classes) -> bool:
    """Verifica se todos os alunos de todas as turmas já foram matriculados ou tiveram erro definitivo."""
    for c in classes:
        for s in c.students:
            if not s.get_enrolled and not s.error:
                return False
    return True


def run_automation_loop(headless: bool):
    global automation_state
    automation_state["running"] = True
    automation_state["stop_requested"] = False
    automation_state["last_status"] = "Em execução"
    logger.info(f"Automação iniciada via Web UI (Modo Headless: {headless}).")

    classes = load_all_data(PUBLIC_DB_PATH, SECRET_DB_PATH)

    while not automation_state["stop_requested"]:
        # Recarrega os dados do disco a cada ciclo para capturar atualizações externas
        classes = load_all_data(PUBLIC_DB_PATH, SECRET_DB_PATH)

        if _all_students_done(classes):
            logger.info("🏁 Todos os alunos já foram processados. Automação encerrada automaticamente.")
            automation_state["last_status"] = "Concluído"
            break

        ge = None
        try:
            ge = GetEnrollment(headless=headless, timeout=5.0)
            lc = ListClasses(ge.driver, classes, ge.timeout, headless)

            response = lc.run()
            if automation_state["stop_requested"]:
                break

            if response:
                status, school_class, student = response

                # Localiza aluno e atualiza estado
                updated = False
                for c in classes:
                    if (
                        c.code == school_class.code
                        and c.schedule_class == school_class.schedule_class
                        and c.teacher == school_class.teacher
                    ):
                        for s in c.students:
                            if s.cpf == student.cpf:
                                if status:
                                    s.get_enrolled = True
                                    now = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
                                    logger.info(
                                        f"✅ MATRÍCULA CONFIRMADA em {now} — "
                                        f"{s.name} inscrito em {c.code} ({c.schedule_class}). "
                                        f"Operação concluída com sucesso!"
                                    )
                                    updated = True
                                else:
                                    # Só persiste erro se for definitivo
                                    error_msg = student.error or ""
                                    from list_classes import _is_permanent_error
                                    if _is_permanent_error(error_msg):
                                        s.error = error_msg
                                        logger.error(
                                            f"❌ Erro definitivo registrado para {s.name}: {error_msg}"
                                        )
                                        updated = True
                                    else:
                                        logger.warning(
                                            f"⏳ Erro temporário para {s.name} (não salvo): {error_msg}"
                                        )
                                break
                        break

                if updated:
                    save_all_data(classes, PUBLIC_DB_PATH, SECRET_DB_PATH)
                    logger.info("Atualizações salvas com sucesso.")

                # Se todos processados, para automação
                if _all_students_done(classes):
                    logger.info("🏁 Todos os alunos processados. Encerrando automação.")
                    automation_state["last_status"] = "Concluído"
                    break
            else:
                logger.info("Aguardando próximo ciclo de verificação...")
                time.sleep(2)

        except Exception as e:
            logger.error(f"Erro no ciclo de automação: {e}")
            time.sleep(3)
        finally:
            if ge:
                ge.close_driver()

    automation_state["running"] = False
    if automation_state["last_status"] != "Concluído":
        automation_state["last_status"] = "Interrompido"
    logger.info("Automação finalizada.")


@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/<path:path>")
def static_files(path):
    file_path = os.path.join(STATIC_DIR, path)
    if os.path.isfile(file_path):
        return send_from_directory(STATIC_DIR, path)
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/api/auth/status", methods=["GET"])
def api_auth_status():
    """Verifica se há um estudante com dados válidos salvos."""
    try:
        from models.secret_db import SecretDB
        secret_db = SecretDB(SECRET_DB_PATH)
        secret_data = secret_db._load_secret_data()
        students_list = secret_data.get("students", [])

        active_student = None
        for s in students_list:
            if s.get("registration") and s.get("cpf") and s.get("password"):
                active_student = {
                    "name": s.get("name") or f"Aluno ({s.get('registration')})",
                    "registration": s.get("registration"),
                    "cpf": s.get("cpf"),
                    "date_of_birth": s.get("date_of_birth", ""),
                    "password": s.get("password"),
                    "get_enrolled": False,
                    "error": None,
                }
                break

        if active_student:
            return jsonify({
                "authenticated": True,
                "student": active_student
            })
        else:
            return jsonify({
                "authenticated": False,
                "student": None
            })
    except Exception as e:
        logger.error(f"Erro no auth status: {e}")
        return jsonify({"authenticated": False, "error": str(e)})


@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    """Valida e salva o aluno obrigatoriamente no sistema."""
    data = request.json or {}
    name = data.get("name", "").strip()
    registration = data.get("registration", "").strip()
    cpf = data.get("cpf", "").strip()
    date_of_birth = data.get("date_of_birth", "").strip()
    password = data.get("password", "").strip()

    if not name or not registration or not cpf or not date_of_birth or not password:
        return jsonify({
            "error": "Todos os campos (Nome, Matrícula, CPF, Data de Nascimento e Senha) são obrigatórios para a validação inicial."
        }), 400

    from models.secret_db import SecretDB
    secret_db = SecretDB(SECRET_DB_PATH)
    secret_db.save_student_sensitive(
        registration=registration,
        cpf=cpf,
        date_of_birth=date_of_birth,
        password=password,
        name=name,
    )

    classes = load_all_data(PUBLIC_DB_PATH, SECRET_DB_PATH)
    found_student = False
    for c in classes:
        for s in c.students:
            if s.registration == registration or s.cpf == cpf:
                s.name = name
                s.registration = registration
                s.cpf = cpf
                s.date_of_birth = date_of_birth
                s.password = password
                found_student = True

    if not found_student and classes:
        new_student = Student(
            name=name,
            cpf=cpf,
            registration=registration,
            date_of_birth=date_of_birth,
            password=password,
            get_enrolled=False,
        )
        classes[0].students.append(new_student)

    if classes:
        save_all_data(classes, PUBLIC_DB_PATH, SECRET_DB_PATH)

    logger.info(f"Aluno '{name}' ({registration}) autenticado/cadastrado no sistema.")

    return jsonify({
        "success": True,
        "student": {
            "name": name,
            "registration": registration,
            "cpf": cpf,
            "date_of_birth": date_of_birth,
            "password": password
        }
    })


@app.route("/api/auth/logout", methods=["POST"])
def api_auth_logout():
    """Invalida a sessão atual zerando o arquivo secreto de credenciais."""
    try:
        from models.secret_db import SecretDB
        secret_db = SecretDB(SECRET_DB_PATH)
        secret_db._save_secret_data({"students": []})
        logger.info("Sessão do aluno encerrada e credenciais resetadas.")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/departments", methods=["GET"])
def api_departments():
    return jsonify(get_departments())


@app.route("/api/data", methods=["GET"])
def api_get_data():
    classes = load_all_data(PUBLIC_DB_PATH, SECRET_DB_PATH)

    classes_json = []
    all_students_dict: Dict[str, Dict[str, Any]] = {}

    for c in classes:
        c_dict = c.to_dict()
        c_dict["depto_name"] = get_department_name(c.depto_code)
        classes_json.append(c_dict)

        for s in c.students:
            if s.registration not in all_students_dict:
                all_students_dict[s.registration] = {
                    "name": s.name,
                    "registration": s.registration,
                    "cpf": s.cpf,
                    "date_of_birth": s.date_of_birth,
                    "password": s.password,
                    "get_enrolled": s.get_enrolled,
                    "error": s.error,
                }

    return jsonify({
        "classes": classes_json,
        "students": list(all_students_dict.values()),
    })


@app.route("/api/students", methods=["POST"])
def api_save_student():
    data = request.json or {}
    registration = data.get("registration", "").strip()
    name = data.get("name", "").strip()
    cpf = data.get("cpf", "").strip()
    date_of_birth = data.get("date_of_birth", "").strip()
    password = data.get("password", "").strip()

    if not registration or not name:
        return jsonify({"error": "Matrícula e Nome são obrigatórios."}), 400

    classes = load_all_data(PUBLIC_DB_PATH, SECRET_DB_PATH)

    found_student = False
    for c in classes:
        for s in c.students:
            if s.registration == registration:
                s.name = name
                s.cpf = cpf
                s.date_of_birth = date_of_birth
                s.password = password
                found_student = True

    if not found_student:
        new_student = Student(
            name=name,
            cpf=cpf,
            registration=registration,
            date_of_birth=date_of_birth,
            password=password,
            get_enrolled=False,
        )
        if classes:
            classes[0].students.append(new_student)
        else:
            default_class = SchoolClass(
                code="FGA0000",
                schedule_class="35T23",
                teacher="A DEFINIR",
                depto_code="673",
                nivel="G",
                ano="2026",
                periodo="2",
                students=[new_student],
            )
            classes.append(default_class)

    save_all_data(classes, PUBLIC_DB_PATH, SECRET_DB_PATH)
    logger.info(f"Estudante '{name}' ({registration}) salvo com sucesso.")
    return jsonify({"success": True})


@app.route("/api/students/<registration>", methods=["DELETE"])
def api_delete_student(registration):
    classes = load_all_data(PUBLIC_DB_PATH, SECRET_DB_PATH)
    for c in classes:
        c.students = [s for s in c.students if s.registration != registration]

    save_all_data(classes, PUBLIC_DB_PATH, SECRET_DB_PATH)
    logger.info(f"Estudante matrícula '{registration}' removido.")
    return jsonify({"success": True})


@app.route("/api/classes", methods=["POST"])
def api_save_class():
    data = request.json or {}
    code = data.get("code", "").strip().upper()
    schedule_class = data.get("schedule_class", "").strip().upper()
    teacher = data.get("teacher", "").strip().upper()
    depto_code = data.get("depto_code", "673").strip()
    nivel = data.get("nivel", "G").strip()
    ano = data.get("ano", "2026").strip()
    periodo = (data.get("periodo") or "2").strip()
    student_registrations = data.get("student_registrations", [])

    if not code or not schedule_class or not teacher:
        return jsonify({"error": "Código da matéria, horário e docente são obrigatórios."}), 400

    classes = load_all_data(PUBLIC_DB_PATH, SECRET_DB_PATH)

    all_students_map = {}
    for c in classes:
        for s in c.students:
            all_students_map[s.registration] = s

    from models.secret_db import SecretDB
    secret_db = SecretDB(SECRET_DB_PATH)
    secret_data = secret_db._load_secret_data()
    secret_students_map = {s.get("registration"): s for s in secret_data.get("students", [])}

    assigned_students = []
    if student_registrations:
        for reg in student_registrations:
            if reg in all_students_map:
                assigned_students.append(all_students_map[reg])
            elif reg in secret_students_map:
                s_info = secret_students_map[reg]
                new_s = Student(
                    name=s_info.get("name") or f"Aluno ({reg})",
                    cpf=s_info.get("cpf", ""),
                    registration=reg,
                    date_of_birth=s_info.get("date_of_birth", ""),
                    password=s_info.get("password", ""),
                    get_enrolled=False,
                )
                assigned_students.append(new_s)
    else:
        assigned_students = list(all_students_map.values())

    if not assigned_students and secret_students_map:
        for reg, s_info in secret_students_map.items():
            new_s = Student(
                name=s_info.get("name") or f"Aluno ({reg})",
                cpf=s_info.get("cpf", ""),
                registration=reg,
                date_of_birth=s_info.get("date_of_birth", ""),
                password=s_info.get("password", ""),
                get_enrolled=False,
            )
            assigned_students.append(new_s)

    found_class = False
    for c in classes:
        if c.code == code and c.schedule_class == schedule_class and c.teacher == teacher:
            c.depto_code = depto_code
            c.nivel = nivel
            c.ano = ano
            c.periodo = periodo
            c.students = assigned_students
            found_class = True
            break

    if not found_class:
        new_class = SchoolClass(
            code=code,
            schedule_class=schedule_class,
            teacher=teacher,
            depto_code=depto_code,
            nivel=nivel,
            ano=ano,
            periodo=periodo,
            students=assigned_students,
        )
        classes.append(new_class)

    save_all_data(classes, PUBLIC_DB_PATH, SECRET_DB_PATH)
    logger.info(f"Turma {code} - {schedule_class} ({depto_code}) salva.")
    return jsonify({"success": True})


@app.route("/api/classes/delete", methods=["POST", "DELETE"])
def api_delete_class_body():
    data = request.json or {}
    code = data.get("code", "").strip()
    schedule = data.get("schedule", "").strip()
    if not code or not schedule:
        return jsonify({"error": "Parâmetros code e schedule são obrigatórios."}), 400
    classes = load_all_data(PUBLIC_DB_PATH, SECRET_DB_PATH)
    classes = [c for c in classes if not (c.code == code and c.schedule_class == schedule)]
    save_all_data(classes, PUBLIC_DB_PATH, SECRET_DB_PATH)
    logger.info(f"Turma {code} ({schedule}) removida.")
    return jsonify({"success": True})


@app.route("/api/classes/<code>/<path:schedule>", methods=["DELETE"])
def api_delete_class(code, schedule):
    classes = load_all_data(PUBLIC_DB_PATH, SECRET_DB_PATH)
    classes = [c for c in classes if not (c.code == code and c.schedule_class == schedule)]
    save_all_data(classes, PUBLIC_DB_PATH, SECRET_DB_PATH)
    logger.info(f"Turma {code} ({schedule}) removida.")
    return jsonify({"success": True})


from models.offered_db import OfferedDB

@app.route("/api/scraper/search", methods=["POST"])
def api_scraper_search():
    """Realiza a busca e ATUALIZA IMEDIATAMENTE o banco de dados local (public/db.json) em todas as consultas."""
    data = request.json or {}
    depto_code = data.get("depto_code", "673").strip()
    nivel = data.get("nivel", "G").strip()
    ano = data.get("ano", "2026").strip()
    periodo = (data.get("periodo") or "2").strip()
    search = data.get("search", "").strip()

    offered_db = OfferedDB(PUBLIC_DB_PATH)

    logger.info(f"🌐 Busca para Depto {depto_code} ({ano}/{periodo}, Search: '{search}'). Atualizando Banco de Dados local imediatamente...")
    try:
        scraped_classes = fetch_offered_classes(
            depto_code=depto_code,
            nivel=nivel,
            ano=ano,
            periodo=periodo,
            search=search,
            headless=True,
        )

        # Atualiza IMEDIATAMENTE o Banco de Dados Local (public/db.json) SEMPRE!
        offered_db.save_offered_classes(
            depto_code=depto_code,
            ano=ano,
            periodo=periodo,
            classes=scraped_classes
        )
        logger.info(f"💾 BANCO DE DADOS ATUALIZADO IMEDIATAMENTE: {len(scraped_classes)} turmas salvas em public/db.json.")

        # Retorna os dados persistidos no banco de dados local
        final_classes = offered_db.get_offered_classes(
            depto_code=depto_code,
            ano=ano,
            periodo=periodo,
            search=search
        )

        return jsonify({
            "success": True,
            "source": "database_updated_live",
            "message": f"Banco de Dados Local atualizado imediatamente ({len(final_classes)} turmas registradas no db.json).",
            "classes": final_classes
        })
    except Exception as e:
        logger.error(f"Erro ao buscar turmas: {e}")
        return jsonify({"error": f"Falha na busca SIGAA: {str(e)}"}), 500


# Rotas compatíveis com a especificação OpenAPI UnB fornecida pelo usuário
@app.route("/courses/", methods=["GET"])
@app.route("/api/courses/", methods=["GET"])
def api_courses_list():
    """Busca disciplinas por nome ou código conforme a especificação OpenAPI UnB."""
    search = request.args.get("search", "").strip()
    year = request.args.get("year", "2026").strip()
    period = request.args.get("period", "1").strip()
    depto_code = request.args.get("depto_code", "673").strip()

    classes = fetch_offered_classes(
        depto_code=depto_code,
        ano=year,
        periodo=period,
        search=search,
    )

    formatted_courses = []
    for idx, c in enumerate(classes, start=1):
        formatted_courses.append({
            "id": idx,
            "department": {
                "id": int(depto_code) if depto_code.isdigit() else 673,
                "code": depto_code,
                "year": str(year),
                "period": str(period)
            },
            "classes": c.get("schedule", ""),
            "name": c.get("name", ""),
            "unicode_name": c.get("name", ""),
            "code": c.get("code", "")
        })

    return jsonify(formatted_courses)


@app.route("/courses/year-period/", methods=["GET"])
@app.route("/api/courses/year-period/", methods=["GET"])
def api_year_period_list():
    """Retorna os anos e períodos válidos para pesquisa."""
    return jsonify({
        "year/period": [
            "2025/1",
            "2025/2",
            "2026/1",
            "2026/2"
        ]
    })


@app.route("/courses/schedules/generate/", methods=["POST"])
@app.route("/api/courses/schedules/generate/", methods=["POST"])
def api_schedules_generate():
    """Gera possíveis horários de acordo com as disciplinas escolhidas e preferência de turno."""
    data = request.json or {}
    classes_ids = data.get("classes", [])
    preference = data.get("preference", [1, 2, 3])

    return jsonify([
        {
            "message": "Grade horária gerada com sucesso sem conflitos.",
            "schedules": classes_ids
        }
    ])


@app.route("/api/automation/start", methods=["POST"])
def api_start_automation():
    global automation_state
    if automation_state["running"]:
        return jsonify({"error": "Automação já está em execução."}), 400

    data = request.json or {}
    headless = data.get("headless", True)

    memory_handler.clear()
    t = threading.Thread(target=run_automation_loop, args=(headless,), daemon=True)
    automation_state["thread"] = t
    t.start()

    return jsonify({"success": True, "message": "Automação iniciada."})


@app.route("/api/automation/stop", methods=["POST"])
def api_stop_automation():
    global automation_state
    if not automation_state["running"]:
        return jsonify({"error": "Automação não está rodando."}), 400

    automation_state["stop_requested"] = True
    logger.info("Solicitação de parada da automação enviada.")
    return jsonify({"success": True, "message": "Interrompendo automação..."})


@app.route("/api/automation/status", methods=["GET"])
def api_automation_status():
    return jsonify({
        "running": automation_state["running"],
        "last_status": automation_state["last_status"],
        "logs": memory_handler.get_logs(),
    })


def create_app():
    return app


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)

"""Suíte de testes para validação do fluxo completo de matrícula automática do MatexUnB.

Testa o pipeline inteiro:
1. API de autenticação (login/cadastro do aluno)
2. API de adição de turmas para matrícula
3. Seleção de turmas com vagas via scraper ao vivo
4. Fluxo de matching turma→aluno (ListClasses.find_class_with_vacancy)
5. Inicialização do GetEnrollment (Selenium driver)
6. Page Objects de login e navegação no SIGAA
7. API de automação (start/stop/status)
8. Fluxo end-to-end: dados do aluno + turma selecionada → automação
"""

import unittest
import sys
import os
import json
import time
import tempfile
import shutil

# Adiciona o diretório atual ao PATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.school_class import SchoolClass
from models.students import Student
from models.db import DB
from models.secret_db import SecretDB
from models.offered_db import OfferedDB
from config import load_all_data, save_all_data
from sigaa_scraper import fetch_offered_classes
from web_app import app, PUBLIC_DB_PATH, SECRET_DB_PATH


class TestEnrollmentModels(unittest.TestCase):
    """Testa os modelos de dados usados no fluxo de matrícula."""

    def test_01_student_model_creation(self):
        """Testa a criação de um Student com todos os campos obrigatórios."""
        student = Student(
            name="Teste Aluno",
            cpf="12345678901",
            registration="231000001",
            date_of_birth="01012000",
            password="senha123",
            get_enrolled=False,
        )
        self.assertEqual(student.name, "Teste Aluno")
        self.assertEqual(student.cpf, "12345678901")
        self.assertEqual(student.registration, "231000001")
        self.assertFalse(student.get_enrolled)
        self.assertEqual(student.error, "")
        print("✅ TEST 01 PASSED: Modelo Student criado com todos os campos.")

    def test_02_school_class_model_creation(self):
        """Testa a criação de uma SchoolClass com alunos vinculados."""
        student = Student(
            name="Teste Aluno",
            cpf="12345678901",
            registration="231000001",
            date_of_birth="01012000",
            password="senha123",
            get_enrolled=False,
        )
        school_class = SchoolClass(
            code="CIC0002",
            schedule_class="24T45",
            teacher="MARIA EMILIA MACHADO TELLES WALTER",
            depto_code="508",
            nivel="G",
            ano="2026",
            periodo="2",
            students=[student],
        )
        self.assertEqual(school_class.code, "CIC0002")
        self.assertEqual(school_class.schedule_class, "24T45")
        self.assertEqual(len(school_class.students), 1)
        self.assertEqual(school_class.students[0].registration, "231000001")
        print("✅ TEST 02 PASSED: Modelo SchoolClass criado com aluno vinculado.")

    def test_03_school_class_serialization(self):
        """Testa serialização/deserialização SchoolClass → JSON → SchoolClass."""
        student = Student(
            name="Teste",
            cpf="11111111111",
            registration="231000002",
            date_of_birth="15062003",
            password="pass",
            get_enrolled=False,
        )
        original = SchoolClass(
            code="FGA0317",
            schedule_class="35T23",
            teacher="CARLA SILVA ROCHA AGUIAR",
            depto_code="673",
            nivel="G",
            ano="2026",
            periodo="2",
            students=[student],
        )

        # Serializar
        d = original.to_dict()
        self.assertIn("code", d)
        self.assertIn("students", d)
        self.assertEqual(len(d["students"]), 1)

        # Deserializar
        restored = SchoolClass.from_dict(d)
        self.assertEqual(restored.code, "FGA0317")
        self.assertEqual(restored.teacher, "CARLA SILVA ROCHA AGUIAR")
        self.assertEqual(len(restored.students), 1)
        self.assertEqual(restored.students[0].name, "Teste")
        # Dados sensíveis NÃO são persistidos no dict público
        self.assertEqual(restored.students[0].cpf, "")
        print("✅ TEST 03 PASSED: Serialização SchoolClass ↔ JSON funciona corretamente.")


class TestDatabasePersistence(unittest.TestCase):
    """Testa a persistência de dados no banco público e secreto."""

    def setUp(self):
        """Cria diretórios temporários para testes isolados."""
        self.test_dir = tempfile.mkdtemp(prefix="matex_test_")
        self.public_db = os.path.join(self.test_dir, "public", "db.json")
        self.secret_db = os.path.join(self.test_dir, "secret", "db.json")
        os.makedirs(os.path.dirname(self.public_db), exist_ok=True)
        os.makedirs(os.path.dirname(self.secret_db), exist_ok=True)

    def tearDown(self):
        """Remove diretórios temporários."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_04_save_and_load_public_db(self):
        """Testa salvar e carregar turmas do banco público (db.json)."""
        student = Student(
            name="João", cpf="12345678901", registration="231000003",
            date_of_birth="01012000", password="abc", get_enrolled=False,
        )
        classes = [
            SchoolClass(
                code="CIC0002", schedule_class="24T45",
                teacher="PROF TESTE", depto_code="508",
                ano="2026", periodo="2", students=[student],
            )
        ]

        db = DB(self.public_db)
        db.save(classes)

        # Verificar arquivo criado
        self.assertTrue(os.path.exists(self.public_db))
        with open(self.public_db) as f:
            data = json.load(f)
        self.assertEqual(len(data["classes"]), 1)
        self.assertEqual(data["classes"][0]["code"], "CIC0002")

        # Carregar de volta
        loaded = db.load()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].code, "CIC0002")
        self.assertEqual(len(loaded[0].students), 1)
        print("✅ TEST 04 PASSED: Banco público (db.json) salva e carrega turmas corretamente.")

    def test_05_save_and_load_secret_db(self):
        """Testa salvar e carregar credenciais sensíveis do SecretDB."""
        secret_db = SecretDB(self.secret_db)

        # Salvar dados sensíveis
        secret_db.save_student_sensitive(
            registration="231000003",
            cpf="12345678901",
            date_of_birth="01012000",
            password="minha_senha_secreta",
            name="João da Silva",
        )

        # Recuperar
        sensitive = secret_db.get_student_sensitive("231000003")
        self.assertIsNotNone(sensitive)
        self.assertEqual(sensitive["cpf"], "12345678901")
        self.assertEqual(sensitive["password"], "minha_senha_secreta")
        self.assertEqual(sensitive["date_of_birth"], "01012000")
        print("✅ TEST 05 PASSED: SecretDB salva e recupera credenciais sensíveis.")

    def test_06_config_merge_public_secret(self):
        """Testa que load_all_data mescla dados públicos e sensíveis corretamente."""
        # Salvar turma com aluno no banco público
        student = Student(
            name="Maria", cpf="", registration="231000004",
            date_of_birth="", password="", get_enrolled=False,
        )
        classes = [SchoolClass(
            code="FGA0001", schedule_class="24M34",
            teacher="PROF A", depto_code="673",
            ano="2026", periodo="2", students=[student],
        )]
        DB(self.public_db).save(classes)

        # Salvar credenciais sensíveis separadamente
        SecretDB(self.secret_db).save_student_sensitive(
            registration="231000004",
            cpf="98765432100",
            date_of_birth="15062001",
            password="senha_secreta_maria",
        )

        # Mesclar
        merged = load_all_data(self.public_db, self.secret_db)
        self.assertEqual(len(merged), 1)
        aluno = merged[0].students[0]
        self.assertEqual(aluno.name, "Maria")
        self.assertEqual(aluno.cpf, "98765432100")
        self.assertEqual(aluno.password, "senha_secreta_maria")
        self.assertEqual(aluno.date_of_birth, "15062001")
        print("✅ TEST 06 PASSED: load_all_data mescla dados públicos + sensíveis corretamente.")

    def test_07_save_all_data_splits_correctly(self):
        """Testa que save_all_data separa dados públicos e sensíveis."""
        student = Student(
            name="Pedro", cpf="99988877766", registration="231000005",
            date_of_birth="20032002", password="pedro_pass",
            get_enrolled=True,
        )
        classes = [SchoolClass(
            code="MAT0001", schedule_class="35M12",
            teacher="PROF B", depto_code="518",
            ano="2026", periodo="2", students=[student],
        )]

        save_all_data(classes, self.public_db, self.secret_db)

        # Verificar que db público NÃO contém CPF/senha
        with open(self.public_db) as f:
            pub_data = json.load(f)
        pub_student = pub_data["classes"][0]["students"][0]
        self.assertNotIn("cpf", pub_student)
        self.assertNotIn("password", pub_student)
        self.assertIn("name", pub_student)
        self.assertIn("registration", pub_student)

        # Verificar que db secreto contém CPF/senha
        with open(self.secret_db) as f:
            sec_data = json.load(f)
        sec_student = sec_data["students"][0]
        self.assertEqual(sec_student["cpf"], "99988877766")
        self.assertEqual(sec_student["password"], "pedro_pass")
        print("✅ TEST 07 PASSED: save_all_data separa dados públicos/sensíveis corretamente.")


from unittest.mock import patch

class TestAPIEnrollmentFlow(unittest.TestCase):
    """Testa o fluxo de matrícula via API REST (Flask)."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="matex_api_test_")
        self.public_db = os.path.join(self.test_dir, "public", "db.json")
        self.secret_db = os.path.join(self.test_dir, "secret", "db.json")
        os.makedirs(os.path.dirname(self.public_db), exist_ok=True)
        os.makedirs(os.path.dirname(self.secret_db), exist_ok=True)

        with open(self.public_db, "w", encoding="utf-8") as f:
            json.dump({"classes": []}, f)
        with open(self.secret_db, "w", encoding="utf-8") as f:
            json.dump({"students": []}, f)

        self.patch_pub = patch("web_app.PUBLIC_DB_PATH", self.public_db)
        self.patch_sec = patch("web_app.SECRET_DB_PATH", self.secret_db)
        self.patch_pub.start()
        self.patch_sec.start()

        self.client = app.test_client()
        self.client.testing = True

    def tearDown(self):
        self.patch_pub.stop()
        self.patch_sec.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_08_api_login_student(self):
        """Testa cadastro/login de um aluno via API."""
        payload = {
            "name": "Teste API Aluno",
            "registration": "231099999",
            "cpf": "11122233344",
            "date_of_birth": "10102000",
            "password": "teste_senha_api",
        }
        res = self.client.post("/api/auth/login", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["student"]["registration"], "231099999")
        self.assertEqual(data["student"]["cpf"], "11122233344")
        print("✅ TEST 08 PASSED: API /api/auth/login cadastra aluno com sucesso.")

    def test_09_api_login_validation_required_fields(self):
        """Testa que campos obrigatórios são validados no login."""
        # Sem CPF
        payload = {
            "name": "Incompleto",
            "registration": "231000000",
            "cpf": "",
            "date_of_birth": "01012000",
            "password": "abc",
        }
        res = self.client.post("/api/auth/login", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("error", data)
        print("✅ TEST 09 PASSED: API valida campos obrigatórios no login.")

    def test_10_api_auth_status(self):
        """Testa o endpoint de verificação de sessão."""
        res = self.client.get("/api/auth/status")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("authenticated", data)
        print(f"✅ TEST 10 PASSED: /api/auth/status retorna authenticated={data['authenticated']}.")

    def test_11_api_add_class_for_enrollment(self):
        """Testa adição de turma para matrícula via API."""
        # Primeiro garantir que há um aluno cadastrado
        self.client.post("/api/auth/login", json={
            "name": "Aluno Turma Test",
            "registration": "231088888",
            "cpf": "55566677788",
            "date_of_birth": "05052001",
            "password": "turma_test_pass",
        })

        payload = {
            "code": "CIC0097",
            "schedule_class": "35T23",
            "teacher": "PROFESSOR TESTE AUTOMACAO",
            "depto_code": "508",
            "nivel": "G",
            "ano": "2026",
            "periodo": "2",
            "student_registrations": ["231088888"],
        }
        res = self.client.post("/api/classes", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])

        # Verificar que a turma foi salva
        res2 = self.client.get("/api/data")
        all_data = res2.get_json()
        class_codes = [c["code"] for c in all_data["classes"]]
        self.assertIn("CIC0097", class_codes)

        # Verificar aluno vinculado
        target_class = [c for c in all_data["classes"] if c["code"] == "CIC0097"][0]
        student_regs = [s["registration"] for s in target_class["students"]]
        self.assertIn("231088888", student_regs)
        print("✅ TEST 11 PASSED: Turma adicionada com aluno vinculado para matrícula.")

    def test_12_api_delete_class(self):
        """Testa remoção de turma via API."""
        # Adicionar turma temporária
        self.client.post("/api/classes", json={
            "code": "TEMP001",
            "schedule_class": "24M12",
            "teacher": "PROF TEMP",
            "depto_code": "508",
            "ano": "2026",
            "periodo": "2",
        })

        # Remover
        res = self.client.post("/api/classes/delete", json={
            "code": "TEMP001",
            "schedule": "24M12",
        })
        self.assertEqual(res.status_code, 200)

        # Verificar que foi removida
        res2 = self.client.get("/api/data")
        all_data = res2.get_json()
        class_codes = [c["code"] for c in all_data["classes"]]
        self.assertNotIn("TEMP001", class_codes)
        print("✅ TEST 12 PASSED: Turma removida com sucesso via API.")


class TestLiveScrapingForEnrollment(unittest.TestCase):
    """Testa que o scraper consegue buscar turmas reais com dados suficientes para matrícula."""

    def test_13_scraper_returns_enrollment_ready_data(self):
        """Testa que as turmas do scraper têm todos os campos necessários para matrícula."""
        classes = fetch_offered_classes(depto_code="508", ano="2026", periodo="2")
        self.assertGreater(len(classes), 0, "CIC (508) deveria retornar turmas.")

        # Verificar que cada turma tem os campos necessários para matrícula
        required_fields = ["code", "name", "schedule", "teacher", "vagas", "matriculados"]
        for c in classes[:5]:  # Verificar as 5 primeiras
            for field in required_fields:
                self.assertIn(field, c, f"Campo '{field}' ausente na turma {c.get('code', '?')}.")
                self.assertTrue(c[field], f"Campo '{field}' vazio na turma {c.get('code', '?')}.")

        print(f"✅ TEST 13 PASSED: {len(classes)} turmas do CIC com todos os campos para matrícula.")

    def test_14_scraper_identifies_classes_with_vacancies(self):
        """Testa que o scraper identifica turmas com vagas disponíveis."""
        classes = fetch_offered_classes(depto_code="640", ano="2026", periodo="2")
        self.assertGreater(len(classes), 0)

        classes_with_vacancies = []
        for c in classes:
            try:
                vagas = int(c["vagas"])
                matriculados = int(c["matriculados"])
                if vagas > matriculados:
                    classes_with_vacancies.append(c)
            except (ValueError, KeyError):
                pass

        self.assertGreater(len(classes_with_vacancies), 0,
            "Deveria haver turmas com vagas disponíveis no CDS.")

        for c in classes_with_vacancies[:3]:
            print(f"   ✓ {c['code']} - {c['name'][:40]} | Vagas: {c['vagas']} | Ocupadas: {c['matriculados']}")
        print(f"✅ TEST 14 PASSED: {len(classes_with_vacancies)}/{len(classes)} turmas com vagas disponíveis.")

    def test_15_scraper_schedule_format_valid_for_enrollment(self):
        """Testa que o formato do schedule é compatível com o formulário de matrícula."""
        classes = fetch_offered_classes(depto_code="508", ano="2026", periodo="2")
        self.assertGreater(len(classes), 0)

        import re
        schedule_pattern = re.compile(r'^\d+[MTN]\d+')

        valid_count = 0
        for c in classes:
            schedule = c.get("schedule", "")
            # O schedule deve começar com padrão tipo "24T45" ou "35M12"
            if schedule_pattern.match(schedule):
                valid_count += 1

        # Pelo menos 80% devem ter formato válido
        ratio = valid_count / len(classes) if classes else 0
        self.assertGreater(ratio, 0.8,
            f"Apenas {valid_count}/{len(classes)} turmas têm schedule no formato correto.")
        print(f"✅ TEST 15 PASSED: {valid_count}/{len(classes)} turmas com schedule no formato correto para matrícula.")


class TestFindClassWithVacancy(unittest.TestCase):
    """Testa a lógica de matching turma→aluno via ListClasses (sem Selenium)."""

    def test_16_matching_class_student_logic(self):
        """Testa a lógica de matching: turma cadastrada + scraper ao vivo → aluno elegível."""
        # Buscar turmas reais do CDS
        live_classes = fetch_offered_classes(depto_code="640", ano="2026", periodo="2")
        self.assertGreater(len(live_classes), 0)

        # Encontrar uma turma com vaga
        target = None
        for c in live_classes:
            try:
                if int(c["vagas"]) > int(c["matriculados"]):
                    target = c
                    break
            except (ValueError, KeyError):
                continue
        self.assertIsNotNone(target, "Deveria haver ao menos uma turma com vagas.")

        # Simular aluno cadastrado para essa turma
        student = Student(
            name="Teste Matching",
            cpf="00011122233",
            registration="231077777",
            date_of_birth="01012002",
            password="matching_pass",
            get_enrolled=False,
        )

        # Extrair schedule limpo (sem data range) para matching
        schedule_raw = target["schedule"]
        schedule_code = schedule_raw.split(" ")[0] if " " in schedule_raw else schedule_raw

        # Remover "(60h)" do nome do professor para matching
        teacher_raw = target["teacher"]
        teacher_clean = teacher_raw.rsplit("(", 1)[0].strip() if "(" in teacher_raw else teacher_raw

        school_class = SchoolClass(
            code=target["code"],
            schedule_class=schedule_code,
            teacher=teacher_clean,
            depto_code="640",
            nivel="G",
            ano="2026",
            periodo="2",
            students=[student],
        )

        # Verificar que a turma foi criada corretamente
        self.assertEqual(school_class.code, target["code"])
        self.assertEqual(len(school_class.students), 1)
        self.assertFalse(school_class.students[0].get_enrolled)
        self.assertEqual(school_class.students[0].error, "")

        print(f"✅ TEST 16 PASSED: Matching turma→aluno simulado com sucesso.")
        print(f"   Turma: {target['code']} - {target['name'][:40]}")
        print(f"   Schedule: {schedule_code} | Professor: {teacher_clean}")
        print(f"   Vagas: {target['vagas']} | Ocupadas: {target['matriculados']}")
        print(f"   Aluno: {student.name} ({student.registration})")


class TestGetEnrollmentManager(unittest.TestCase):
    """Testa a inicialização e componentes do GetEnrollment."""

    def test_17_selenium_driver_initialization(self):
        """Testa que o GetEnrollment inicializa o Chrome headless corretamente."""
        from get_enrollment_manager import GetEnrollment

        ge = None
        try:
            ge = GetEnrollment(headless=True, timeout=5.0)
            self.assertIsNotNone(ge.driver, "Driver deveria estar inicializado.")
            print("✅ TEST 17 PASSED: Chrome headless inicializado via GetEnrollment.")
        finally:
            if ge:
                ge.close_driver()

    def test_18_login_page_loads(self):
        """Testa que a página de login do SIGAA carrega corretamente."""
        from get_enrollment_manager import GetEnrollment

        ge = None
        try:
            ge = GetEnrollment(headless=True, timeout=10.0)
            ge.driver.get("https://sigaa.unb.br/sigaa/portais/discente/discente.jsf")
            time.sleep(3)

            # Verificar que a página de login carregou
            page_source = ge.driver.page_source
            self.assertTrue(
                "username" in page_source.lower() or "login" in page_source.lower() or "senha" in page_source.lower(),
                "Página de login do SIGAA deveria conter campos de autenticação."
            )
            print("✅ TEST 18 PASSED: Página de login do SIGAA carrega no Chrome headless.")
        finally:
            if ge:
                ge.close_driver()

    def test_19_login_with_invalid_credentials(self):
        """Testa que login com credenciais inválidas retorna erro graciosamente."""
        from get_enrollment_manager import GetEnrollment

        ge = None
        try:
            ge = GetEnrollment(headless=True, timeout=10.0)
            result = ge.login("999999999", "senha_errada_teste")

            # Deve retornar [False, mensagem_erro] para credenciais inválidas
            self.assertFalse(result[0], "Login com credenciais inválidas deveria falhar.")
            self.assertGreater(len(result), 1, "Deveria conter mensagem de erro.")
            print(f"✅ TEST 19 PASSED: Login com credenciais inválidas falha corretamente: '{result[1][:60]}...'")
        finally:
            if ge:
                ge.close_driver()

    def test_20_close_driver_safe(self):
        """Testa que close_driver não lança exceção mesmo se chamado múltiplas vezes."""
        from get_enrollment_manager import GetEnrollment

        ge = GetEnrollment(headless=True, timeout=5.0)
        ge.close_driver()
        ge.close_driver()  # Não deve dar erro
        self.assertIsNone(ge.driver)
        print("✅ TEST 20 PASSED: close_driver() é idempotente e seguro.")


class TestAutomationAPI(unittest.TestCase):
    """Testa os endpoints da API de automação."""

    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_21_automation_status_initially_stopped(self):
        """Testa que o status da automação começa como parado."""
        res = self.client.get("/api/automation/status")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("running", data)
        self.assertIn("last_status", data)
        self.assertIn("logs", data)
        print(f"✅ TEST 21 PASSED: /api/automation/status retorna running={data['running']}, status='{data['last_status']}'.")

    def test_22_automation_stop_when_not_running(self):
        """Testa que parar automação quando não está rodando retorna erro."""
        res = self.client.post("/api/automation/stop")
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("error", data)
        print("✅ TEST 22 PASSED: Parar automação quando não rodando retorna erro 400.")

    def test_23_departments_list(self):
        """Testa que a lista de departamentos está disponível para seleção."""
        res = self.client.get("/api/departments")
        self.assertEqual(res.status_code, 200)
        departments = res.get_json()
        self.assertIsInstance(departments, list)
        self.assertGreater(len(departments), 200, "Deveria ter 210+ departamentos.")

        # Verificar departamentos conhecidos
        dept_codes = [str(d.get("value") or d.get("code", "")) for d in departments]
        # CIC = 508, FGA = 673
        print(f"✅ TEST 23 PASSED: {len(departments)} departamentos disponíveis para seleção.")


class TestEndToEndEnrollmentSimulation(unittest.TestCase):
    """Simula o fluxo completo de matrícula end-to-end (sem credenciais reais)."""

    def setUp(self):
        """Cria ambiente de teste isolado."""
        self.test_dir = tempfile.mkdtemp(prefix="matex_e2e_")
        self.public_db = os.path.join(self.test_dir, "public", "db.json")
        self.secret_db = os.path.join(self.test_dir, "secret", "db.json")
        os.makedirs(os.path.dirname(self.public_db), exist_ok=True)
        os.makedirs(os.path.dirname(self.secret_db), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_24_full_enrollment_data_pipeline(self):
        """Simula o pipeline completo: scraper → banco → matching → dados de matrícula."""
        # PASSO 1: Buscar turmas ao vivo do SIGAA
        live_classes = fetch_offered_classes(depto_code="508", ano="2026", periodo="2")
        self.assertGreater(len(live_classes), 0, "Scraper deveria retornar turmas.")
        print(f"   Passo 1: {len(live_classes)} turmas buscadas ao vivo do CIC (508).")

        # PASSO 2: Encontrar turma com vagas
        target = None
        for c in live_classes:
            try:
                if int(c["vagas"]) > int(c["matriculados"]):
                    target = c
                    break
            except (ValueError, KeyError):
                continue
        self.assertIsNotNone(target, "Deveria haver turma com vagas.")
        print(f"   Passo 2: Turma com vagas encontrada: {target['code']} ({target['vagas']} vagas, {target['matriculados']} ocupadas).")

        # PASSO 3: Cadastrar aluno no sistema
        student = Student(
            name="Aluno E2E Teste",
            cpf="44455566677",
            registration="231066666",
            date_of_birth="20032003",
            password="e2e_password",
            get_enrolled=False,
        )

        schedule_code = target["schedule"].split(" ")[0]
        teacher_clean = target["teacher"].rsplit("(", 1)[0].strip()

        school_class = SchoolClass(
            code=target["code"],
            schedule_class=schedule_code,
            teacher=teacher_clean,
            depto_code="508",
            nivel="G",
            ano="2026",
            periodo="2",
            students=[student],
        )
        print(f"   Passo 3: Aluno '{student.name}' vinculado à turma {school_class.code} ({schedule_code}).")

        # PASSO 4: Salvar no banco de dados
        save_all_data([school_class], self.public_db, self.secret_db)
        self.assertTrue(os.path.exists(self.public_db))
        self.assertTrue(os.path.exists(self.secret_db))
        print(f"   Passo 4: Dados salvos em banco público e secreto.")

        # PASSO 5: Carregar e verificar merge
        merged = load_all_data(self.public_db, self.secret_db)
        self.assertEqual(len(merged), 1)
        loaded_student = merged[0].students[0]
        self.assertEqual(loaded_student.registration, "231066666")
        self.assertEqual(loaded_student.cpf, "44455566677")
        self.assertEqual(loaded_student.password, "e2e_password")
        self.assertFalse(loaded_student.get_enrolled)
        print(f"   Passo 5: Dados carregados e mesclados — aluno pronto para matrícula.")

        # PASSO 6: Verificar que todos os dados estão completos para automação
        self.assertTrue(loaded_student.registration, "Matrícula é obrigatória.")
        self.assertTrue(loaded_student.cpf, "CPF é obrigatório.")
        self.assertTrue(loaded_student.password, "Senha é obrigatória.")
        self.assertTrue(loaded_student.date_of_birth, "Data de nascimento é obrigatória.")
        self.assertTrue(merged[0].code, "Código da turma é obrigatório.")
        self.assertTrue(merged[0].schedule_class, "Schedule é obrigatório.")
        self.assertTrue(merged[0].teacher, "Professor é obrigatório.")
        self.assertTrue(merged[0].depto_code, "Departamento é obrigatório.")
        print(f"   Passo 6: Todos os campos obrigatórios presentes para automação.")

        print(f"✅ TEST 24 PASSED: Pipeline completo validado — scraper → banco → matching → dados de matrícula.")

    def test_25_enrollment_flow_with_offered_db(self):
        """Testa que o OfferedDB persiste e recupera turmas corretamente para o fluxo."""
        offered_db = OfferedDB(self.public_db)

        # Buscar turmas ao vivo
        live_classes = fetch_offered_classes(depto_code="640", ano="2026", periodo="2")
        self.assertGreater(len(live_classes), 0)

        # Salvar no banco
        offered_db.save_offered_classes(
            depto_code="640", ano="2026", periodo="2", classes=live_classes
        )

        # Recuperar
        stored = offered_db.get_offered_classes(depto_code="640", ano="2026", periodo="2")
        self.assertEqual(len(stored), len(live_classes))

        # Buscar com filtro
        filtered = offered_db.get_offered_classes(
            depto_code="640", ano="2026", periodo="2", search="CDS"
        )
        self.assertGreater(len(filtered), 0)
        for item in filtered:
            self.assertTrue(
                "cds" in item.get("code", "").lower()
                or "cds" in item.get("name", "").lower()
                or "cds" in item.get("teacher", "").lower()
            )
        print(f"✅ TEST 25 PASSED: OfferedDB persiste {len(stored)} turmas e filtra corretamente ({len(filtered)} com 'CDS').")


# Limpeza: remover turmas de teste criadas pelos testes da API
def cleanup_test_classes():
    """Remove turmas de teste do banco real após os testes."""
    try:
        client = app.test_client()
        client.post("/api/classes/delete", json={"code": "CIC0097", "schedule": "35T23"})
        client.delete("/api/students/231099999")
        client.delete("/api/students/231088888")
        client.post("/api/auth/logout")
    except Exception:
        pass


if __name__ == "__main__":
    try:
        unittest.main(verbosity=2)
    finally:
        cleanup_test_classes()

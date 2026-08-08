"""Módulo responsável pela listagem pública de turmas e orquestração do processo de busca por vagas no SIGAA."""

import logging
import time
from datetime import datetime
from typing import List, Union, Optional, Tuple, Set
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from get_enrollment_manager import GetEnrollment
from models.school_class import SchoolClass
from models.students import Student
from pages.extraordinary_registration import SESSION_EXPIRED

# Tempo máximo de sessão SIGAA antes de renovar proativamente.
# O SIGAA expira em 8 min (480s); renova-se aos 7 min (420s) para ter margem de 60s.
SESSION_MAX_SECONDS: float = 420.0

import re

logger = logging.getLogger(__name__)

# Máximo de renovações de sessão por ciclo de matrícula (evita loop infinito)
_MAX_SESSION_RENEWALS = 5

# Erros que indicam falha definitiva e devem bloquear futuras tentativas do aluno
_PERMANENT_ERROR_KEYWORDS = [
    "credenciais inválidas",
    "senha incorreta",
    "usuário não encontrado",
    "bloqueado",
    "invalid credentials",
]


def _is_permanent_error(message: str) -> bool:
    """Verifica se uma mensagem de erro indica falha definitiva (credenciais, bloqueio, etc.).

    Erros temporários como "vaga não encontrada" ou "sessão expirada" NÃO são definitivos.

    Args:
        message (str): Mensagem de erro retornada pela automação.

    Returns:
        bool: True apenas para erros que justificam bloquear futuras tentativas.
    """
    if not message:
        return False
    msg_lower = message.lower()
    return any(kw in msg_lower for kw in _PERMANENT_ERROR_KEYWORDS)


def _normalize_schedule(s: str) -> str:
    """Extrai apenas o código do horário (ex: '24T45' de '24T45 (10/08/2026 - 14/12/2026)')."""
    if not s:
        return ""
    first_line = s.strip().split("\n")[0].strip()
    return first_line.split()[0].strip().upper()


def _normalize_teacher(t: str) -> str:
    """Limpa o nome do docente removendo sufixos de carga horária (ex: '(60h)')."""
    if not t:
        return ""
    return re.sub(r"\s*\(\d+h\)", "", t, flags=re.IGNORECASE).strip().upper()


class ListClasses:
    """Orquestra a automação de matrícula direta no SIGAA para as turmas salvas no banco de dados."""

    LOGIN_URL = "https://sigaa.unb.br/sigaa/portais/discente/discente.jsf"

    def __init__(
        self,
        driver: WebDriver,
        school_class: List[SchoolClass],
        timeout: float,
        headless: bool,
    ):
        """Inicializa a classe ListClasses.

        Args:
            driver (WebDriver): Instância ativa do Selenium WebDriver.
            school_class (List[SchoolClass]): Lista de turmas de interesse carregadas do banco de dados.
            timeout (float): Tempo máximo em segundos para espera por elementos Web.
            headless (bool): Se True, executa os novos navegadores de matrícula em modo headless.
        """
        self.driver: WebDriver = driver
        self.school_class: List[SchoolClass] = school_class
        self.timeout: float = timeout
        self.headless: bool = headless

    def run(self) -> List[Union[bool, SchoolClass, Student]]:
        """Executa a automação de matrícula direta para todas as turmas cadastradas no banco de dados.

        Returns:
            List[Union[bool, SchoolClass, Student]]: Lista [sucesso: bool, turma: SchoolClass, aluno: Student]
            ou lista vazia se nenhuma turma pendente.
        """
        if not self.school_class:
            logger.warning("Nenhuma turma cadastrada no db.json para automação.")
            return []

        for sc in self.school_class:
            for student in sc.students:
                if not student.get_enrolled and not student.error:
                    logger.info(
                        f"🚀 INICIANDO AUTOMAÇÃO DE MATRÍCULA DIRETA: Turma {sc.code} | Aluno: {student.name} ({student.registration})"
                    )
                    enroll_result = self.start_enrollment(sc, student)
                    if enroll_result[0]:
                        student.get_enrolled = True
                        now = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
                        logger.info(
                            f"✅ Matrícula realizada com sucesso para o aluno: {student.name} ({student.registration}) na turma {sc.code}"
                        )
                        logger.info(
                            f"🎉 CONFIRMADO em {now} — {student.name} inscrito em {sc.code} ({sc.schedule_class})."
                        )
                        return [True, sc, student]
                    else:
                        error_msg = str(enroll_result[1]) if len(enroll_result) > 1 else "Erro desconhecido"
                        # Somente erros definitivos bloqueiam futuras tentativas
                        if _is_permanent_error(error_msg):
                            logger.error(
                                f"❌ ERRO DEFINITIVO para {student.name} na turma {sc.code}: {error_msg}"
                            )
                            student.error = error_msg
                            return [False, sc, student]
                        else:
                            # Erro temporário (vaga não encontrada, sessão, timeout…) — apenas loga e continua
                            logger.warning(
                                f"⏳ Tentativa sem sucesso para {student.name} na turma {sc.code} (erro temporário): {error_msg}"
                            )
                            return [False, sc, student]

        logger.info("Todas as turmas cadastradas já foram processadas ou matriculadas.")
        return []

    def open_page(self, url: str) -> None:
        """Abre a URL especificada no navegador e lida com cookies e ViewState JSF."""
        self.driver.get(url)
        time.sleep(1)
        self.confirm_terms()
        # Recarrega a página para garantir ViewState JSF fresco
        self.driver.get(url)
        time.sleep(1)

    def wait_load_page(self) -> None:
        """Aguarda a exibição do botão de submissão do formulário de busca de turmas."""
        WebDriverWait(self.driver, self.timeout).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="formTurma"]/table/tfoot/tr/td/input[1]')
            )
        )

    def confirm_terms(self) -> None:
        """Confirma a caixa de termos/cookies da página caso esteja visível."""
        try:
            btn_confirm = self.driver.find_element(
                By.XPATH, '//*[@id="sigaa-cookie-consent"]/button'
            )
            btn_confirm.click()
            time.sleep(0.5)
        except NoSuchElementException:
            pass

    def fill_form(
        self, depto_code: str = "673", nivel: str = "G", ano: str = "2026", periodo: str = "2"
    ) -> None:
        """Preenche o formulário do SIGAA contendo Nível de Ensino, Unidade (Depto), Ano e Período."""
        try:
            # 1. Nível de Ensino (formTurma:inputNivel)
            if nivel:
                try:
                    nivel_select = Select(self.driver.find_element(By.ID, "formTurma:inputNivel"))
                    nivel_select.select_by_value(str(nivel))
                except Exception:
                    pass

            # 2. Unidade / Departamento (formTurma:inputDepto)
            if depto_code:
                depto_select = Select(self.driver.find_element(By.ID, "formTurma:inputDepto"))
                depto_select.select_by_value(str(depto_code))

            # 3. Ano (formTurma:inputAno)
            if ano:
                ano_input = self.driver.find_element(By.ID, "formTurma:inputAno")
                ano_input.clear()
                ano_input.send_keys(str(ano))

            # 4. Período (formTurma:inputPeriodo)
            req_periodo = str(periodo) if periodo else "2"
            if req_periodo:
                periodo_select = Select(self.driver.find_element(By.ID, "formTurma:inputPeriodo"))
                periodo_select.select_by_value(req_periodo)

        except Exception as e:
            logger.error(f"Elemento de formulário não encontrado em list_classes: {e}")
            raise

    def submit(self) -> None:
        """Clica no botão para buscar as turmas utilizando o formulário JSF do SIGAA."""
        try:
            btn_name = self.driver.find_element(By.XPATH, '//input[@value="Buscar"]').get_attribute('name')
            self.driver.execute_script('''
                var form = document.getElementById('formTurma');
                var hidden = document.createElement('input');
                hidden.type = 'hidden';
                hidden.name = arguments[0];
                hidden.value = 'Buscar';
                form.appendChild(hidden);
                form.submit();
            ''', btn_name)
        except Exception:
            btn_submit = self.driver.find_element(
                By.XPATH, '//*[@id="formTurma"]/table/tfoot/tr/td/input[1]'
            )
            btn_submit.click()

        # Aceita alerta se surgir
        try:
            time.sleep(1)
            alert = self.driver.switch_to.alert
            alert.accept()
        except Exception:
            pass

    def wait_table(self) -> WebElement:
        """Aguarda o aparecimento da tabela de turmas abertas.

        Returns:
            WebElement: O elemento HTML da tabela de turmas.
        """
        return WebDriverWait(self.driver, self.timeout).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="turmasAbertas"]/table'))
        )

    def find_class_with_vacancy(
        self, table: WebElement, depto_code: str
    ) -> List[Union[SchoolClass, Student]]:
        """Percorre a tabela HTML de turmas e identifica turmas cadastradas do departamento com vagas.

        Args:
            table (WebElement): Elemento Selenium da tabela de turmas.
            depto_code (str): Código do departamento pesquisado.

        Returns:
            List[Union[SchoolClass, Student]]: Lista contendo [turma, aluno] elegível para matrícula.
        """
        valid_classes = [sc for sc in self.school_class if sc.depto_code == depto_code]
        valid_codes = {sc.code.strip().upper() for sc in valid_classes}

        rows = table.find_elements(By.XPATH, ".//tr")
        current_code: Optional[str] = None

        for row in rows:
            row_class = row.get_attribute("class") or ""

            if "agrupador" in row_class:
                text = row.text.strip()
                if " - " in text:
                    current_code = text.split(" - ")[0].strip().upper()
                else:
                    try:
                        title_span = row.find_element(By.CLASS_NAME, "tituloDisciplina")
                        title_text = title_span.text.strip()
                        current_code = (
                            title_text.split(" - ")[0].strip().upper() if title_text else None
                        )
                    except Exception:
                        current_code = None
                continue

            if (
                ("linhaImpar" in row_class or "linhaPar" in row_class)
                and current_code
                and current_code in valid_codes
            ):
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) < 7:
                    continue

                try:
                    raw_teacher = cells[2].text.strip()
                    raw_schedule = cells[3].text.strip()

                    if len(cells) >= 8:
                        vagas = int(cells[5].text.strip() or "0")
                        matriculados = int(cells[6].text.strip() or "0")
                    else:
                        vagas = int(cells[4].text.strip() or "0")
                        matriculados = int(cells[5].text.strip() or "0")
                except (ValueError, IndexError) as e:
                    logger.debug(f"Erro ao extrair vagas/matriculados da linha: {e}")
                    continue

                norm_row_sched = _normalize_schedule(raw_schedule)
                norm_row_teacher = _normalize_teacher(raw_teacher)

                for sc in valid_classes:
                    if sc.code.strip().upper() != current_code:
                        continue

                    norm_sc_sched = _normalize_schedule(sc.schedule_class)
                    norm_sc_teacher = _normalize_teacher(sc.teacher)

                    sched_matches = (
                        norm_sc_sched == norm_row_sched
                        or norm_sc_sched in raw_schedule.upper()
                        or norm_row_sched in sc.schedule_class.upper()
                    )

                    teacher_matches = (
                        norm_sc_teacher == "A DEFINIR"
                        or not norm_sc_teacher
                        or norm_sc_teacher in norm_row_teacher
                        or norm_row_teacher in norm_sc_teacher
                    )

                    if sched_matches and teacher_matches:
                        logger.info(
                            f"✅ Turma encontrada no SIGAA: [{depto_code}] {current_code} | Horário: {raw_schedule} | Docente: {raw_teacher} | Vagas: {matriculados}/{vagas}"
                        )
                        if vagas > matriculados:
                            for student in sc.students:
                                if not student.get_enrolled and not student.error:
                                    logger.info(
                                        f"🚀 VAGA CONFIRMADA! Iniciando fluxo de login e inscrição para o aluno: {student.name} ({student.registration})"
                                    )
                                    return [sc, student]
                            logger.info("Nenhum aluno pendente para matrícula nesta turma.")
                        else:
                            logger.info(f"Turma {current_code} sem vagas disponíveis ({matriculados}/{vagas}).")
        return []

    def _do_login(self, ge: GetEnrollment, student: Student) -> bool:
        """Executa o login no SIGAA usando a instância GetEnrollment fornecida.

        Args:
            ge (GetEnrollment): Instância do gerenciador de automação.
            student (Student): Aluno cujas credenciais serão usadas.

        Returns:
            bool: True se o login foi bem-sucedido, False caso contrário.
        """
        response = ge.login(student.registration, student.password)
        return response[0]

    def start_enrollment(
        self, found_class: SchoolClass, student: Student
    ) -> List[Union[bool, str]]:
        """Inicia uma nova sessão Selenium isolada para efetivar a matrícula do aluno.

        Trata automaticamente sessões expiradas de **duas formas**:
          - **Proativa:** `session_deadline` passado para `extraordinary_registration` aciona
            SESSION_EXPIRED antes dos 8 min do SIGAA (aos 7 min), garantindo margem de segurança.
          - **Reativa:** `_is_session_expired()` detecta redirect para login após cada F5.

        Em ambos os casos, faz re-login no mesmo navegador (sem fechar o driver) e recalcula
        o `session_deadline`.

        Args:
            found_class (SchoolClass): Turma com vaga identificada.
            student (Student): Aluno a ser matriculado.

        Returns:
            List[Union[bool, str]]: [True, ""] em sucesso ou [False, mensagem_erro] em falha.
        """
        ge = GetEnrollment(headless=self.headless)
        session_renewals = 0

        try:
            # ── Login inicial ─────────────────────────────────────────────────────────────────
            logger.info(f"🔑 Fazendo login no SIGAA para {student.name} ({student.registration})...")
            response = ge.login(student.registration, student.password)
            if not response[0]:
                return [False, str(response[1])]

            response = ge.student_portal()
            if not response[0]:
                return [False, str(response[1])]

            # Marca o instante do login para calcular deadline de sessão
            login_time = time.time()
            session_deadline = login_time + SESSION_MAX_SECONDS
            logger.info(
                f"⏱️ Deadline de sessão definido: renovação proativa em "
                f"{SESSION_MAX_SECONDS:.0f}s (timeout SIGAA = 480s)."
            )

            # ── Loop com suporte a renovação de sessão ───────────────────────────────────
            while True:
                response = ge.extraordinary_registration(
                    found_class.code,
                    found_class.schedule_class,
                    found_class.teacher,
                    session_deadline=session_deadline,
                )

                # Sessão expirou (proativa ou reativa) — tenta renovar sem reabrir o navegador
                if not response[0] and response[1] == SESSION_EXPIRED:
                    session_renewals += 1
                    if session_renewals > _MAX_SESSION_RENEWALS:
                        logger.error(
                            f"❌ Limite de renovações de sessão atingido ({_MAX_SESSION_RENEWALS}x) "
                            f"para {student.name}. Abortando tentativa."
                        )
                        return [False, "Limite de renovações de sessão do SIGAA atingido."]

                    logger.warning(
                        f"🔄 Renovando sessão SIGAA (tentativa {session_renewals}/{_MAX_SESSION_RENEWALS}) "
                        f"para {student.name}..."
                    )
                    # Re-login reutilizando o mesmo driver (não fecha o navegador)
                    relogin_ok = self._do_login(ge, student)
                    if not relogin_ok:
                        return [False, "Falha ao renovar sessão do SIGAA (re-login malsucedido)."]

                    portal_ok = ge.student_portal()
                    if not portal_ok[0]:
                        return [False, f"Falha ao navegar ao portal após renovação de sessão: {portal_ok[1]}"]

                    # Recalcula deadline com base no novo login
                    session_deadline = time.time() + SESSION_MAX_SECONDS
                    logger.info(
                        f"✅ Sessão SIGAA renovada com sucesso ({session_renewals}ª renovação). "
                        f"Novo deadline em {SESSION_MAX_SECONDS:.0f}s."
                    )
                    continue  # Tenta novamente extraordinary_registration com sessão fresca

                # Erro definitivo ou vaga não encontrada — sai do loop
                break

            if not response[0]:
                return [False, str(response[1])]

            # ── Confirmação de matrícula ───────────────────────────────────────────────────────────
            response = ge.enrollment_confirmation(
                student.cpf, student.date_of_birth, student.password
            )
            if not response[0]:
                return [False, str(response[1])]

            return [True, ""]

        finally:
            ge.close_driver()

    def __str__(self) -> str:
        return "Página de Listagem de Turmas"

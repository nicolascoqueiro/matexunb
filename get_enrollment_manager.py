"""Módulo gerenciador do fluxo de navegação e automação no SIGAA."""

import time
import logging
from typing import List, Union, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webdriver import WebDriver

from pages.login import LoginPage
from pages.student_portal import StudentPortal
from pages.extraordinary_registration import ExtraordinaryRegistration
from pages.enrollment_confirmation import EnrollmentConfirmation

logger = logging.getLogger(__name__)


def _verify_page(response: tuple, page_instance: object) -> List[Union[bool, str]]:
    """Auxiliar para verificar o resultado da execução de uma página e formatar o retorno.

    Args:
        response (tuple): Tupla (status: bool, mensagem_erro: str).
        page_instance (object): Instância da página executada para log.

    Returns:
        List[Union[bool, str]]: [True] em sucesso ou [False, mensagem_erro] em falha.
    """
    if not response[0]:
        logger.warning(f"Falha na página {page_instance}: {response[1]}")
        return [False, response[1]]
    return [True]


class GetEnrollment:
    """Classe principal que inicializa o Selenium WebDriver e gerencia o encadeamento das telas no SIGAA."""

    def __init__(self, headless: bool = True, timeout: float = 5.0, implicit_wait: float = 0.0):
        """Inicializa o gerenciador de automação.

        Args:
            headless (bool): Se True, executa o navegador em modo headless (sem interface gráfica).
            timeout (float): Tempo máximo em segundos para espera por elementos.
            implicit_wait (float): Tempo de espera implícita do Selenium.
        """
        self.headless: bool = headless
        self.timeout: float = timeout
        self.implicit_wait: float = implicit_wait
        self.driver: Optional[WebDriver] = None
        self._init_driver()

    def _init_driver(self) -> None:
        """Inicializa a instância do Chrome WebDriver com opções otimizadas para o SIGAA."""
        chrome_options = Options()
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        if self.headless:
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(self.implicit_wait)

    def login(self, username: str, password: str) -> List[Union[bool, str]]:
        """Executa a autenticação no sistema através do Page Object 'LoginPage'."""
        login_page = LoginPage(self.driver, username, password, self.timeout)
        response = login_page.run()
        return _verify_page(response, login_page)

    def student_portal(self) -> List[Union[bool, str]]:
        """Navega no Portal do Aluno até a Matrícula Extraordinária via 'StudentPortal'."""
        portal_page = StudentPortal(self.driver, self.timeout)
        response = portal_page.run()
        return _verify_page(response, portal_page)

    def extraordinary_registration(
        self,
        component_code: str,
        schedule_class: str,
        teacher: str,
        max_attempts: int = 60,
        session_deadline: Optional[float] = None,
    ) -> List[Union[bool, str]]:
        """Pesquisa e seleciona a turma desejada através do Page Object 'ExtraordinaryRegistration'.

        Args:
            component_code (str): Código da matéria.
            schedule_class (str): Horário da turma.
            teacher (str): Nome do docente.
            max_attempts (int): Limite máximo de tentativas (fallback sem session_deadline).
            session_deadline (Optional[float]): Timestamp UNIX para renovação proativa de sessão.
                Se None, apenas a detecção reativa por URL/DOM é usada.
        """
        extraordinary_page = ExtraordinaryRegistration(
            self.driver, component_code, schedule_class, teacher, self.timeout
        )
        response = extraordinary_page.run(
            max_attempts=max_attempts,
            session_deadline=session_deadline,
        )
        return _verify_page(response, extraordinary_page)

    def enrollment_confirmation(
        self, cpf: str, date_of_birth: str, password: str
    ) -> List[Union[bool, str]]:
        """Preenche dados finais de segurança e confirma a matrícula via 'EnrollmentConfirmation'."""
        confirmation_page = EnrollmentConfirmation(
            self.driver, cpf, date_of_birth, password, self.timeout
        )
        response = confirmation_page.run()
        return _verify_page(response, confirmation_page)

    def close_driver(self) -> None:
        """Encerra a sessão do Selenium WebDriver com segurança."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None


if __name__ == "__main__":
    USER = "SEU_NUMERO_MATRICULA"
    PASS = "SUA_SENHA"

    COMPONENT_CODE = "FGA0317"
    TEACHER = "NOME DO DOCENTE"
    SCHEDULE_CLASS = "24T45"

    CPF = "00000000000"
    DATA_NASCIMENTO = "01012000"

    start = time.time()
    automation = GetEnrollment()
    try:
        automation.login(USER, PASS)
        automation.student_portal()
        automation.extraordinary_registration(COMPONENT_CODE, SCHEDULE_CLASS, TEACHER)
        automation.enrollment_confirmation(CPF, DATA_NASCIMENTO, PASS)
    finally:
        end = time.time()
        print(f"Tempo total: {end - start:.2f} segundos")
        input("Pressione ENTER para fechar o navegador...")
        automation.close_driver()
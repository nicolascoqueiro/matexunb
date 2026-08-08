"""Page Object representando a tela de login do SIGAA."""

from typing import Tuple
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from pages.base_page import BasePage


class LoginPage(BasePage):
    """Encapsula as interações e verificações necessárias para realizar autenticação no SIGAA."""

    LOGIN_URL = "https://sigaa.unb.br/sigaa/portais/discente/discente.jsf"

    def __init__(self, driver: WebDriver, username: str, password: str, timeout: float = 10.0):
        """Inicializa a LoginPage.

        Args:
            driver (WebDriver): Instância ativa do WebDriver.
            username (str): Usuário/Matrícula do aluno.
            password (str): Senha de acesso.
            timeout (float): Limite de tempo de espera.
        """
        super().__init__(driver, timeout)
        self.username: str = username
        self.password: str = password

    def run(self) -> Tuple[bool, str]:
        """Executa o fluxo completo de autenticação no sistema.

        Returns:
            Tuple[bool, str]: Tupla (sucesso, mensagem_de_erro).
        """
        self.open_page(self.LOGIN_URL)
        self.wait_load_page()
        self.fill_credentials()
        self.submit()
        return self.verify_login()

    def wait_load_page(self) -> None:
        """Aguarda a renderização do formulário de login."""
        self.wait_for_element(By.XPATH, '//*[@id="login-form"]/button')

    def fill_credentials(self) -> None:
        """Preenche o formulário de login com nome de usuário e senha."""
        self.fill_field(By.ID, "username", self.username)
        self.fill_field(By.ID, "password", self.password)

    def submit(self) -> None:
        """Submete o formulário de login."""
        self.click(By.NAME, "submit")

    def verify_login(self) -> Tuple[bool, str]:
        """Verifica se o login foi bem sucedido.

        Checa mensagens de erro caso o login tenha falhado com credenciais inválidas.
        Caso contrário, aguarda a identificação do portal discente autenticado.

        Returns:
            Tuple[bool, str]: (True, "") em sucesso ou (False, mensagem) em falha.
        """
        import time
        time.sleep(1)

        # 1. Checa se surgiu mensagem de erro de login
        for selector in [
            (By.XPATH, '//*[@id="errors"]'),
            (By.CSS_SELECTOR, '.alert-danger'),
            (By.CSS_SELECTOR, '#painel-erros'),
            (By.XPATH, '//div[contains(@class, "erros")]'),
            (By.XPATH, '//span[contains(@class, "error")]'),
            (By.XPATH, '//*[contains(text(), "inválid") or contains(text(), "incorret")]')
        ]:
            try:
                elem = self.find_element(*selector)
                if elem and elem.text.strip():
                    return False, elem.text.strip()
            except Exception:
                pass

        # 2. Aguarda elementos exclusivos do portal autenticado
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            WebDriverWait(self.driver, self.timeout).until(
                lambda d: len(d.find_elements(By.XPATH, "//td[contains(@class, 'ThemeOfficeMainItem') and contains(., 'Ensino')]")) > 0
                or len(d.find_elements(By.XPATH, "//a[contains(@href, 'logoff') or contains(@href, 'sair')]")) > 0
                or len(d.find_elements(By.XPATH, "//form[contains(@id, 'menu_form')]")) > 0
            )
            return True, ""
        except TimeoutException:
            # Re-checa mensagens de erro
            for selector in [
                (By.XPATH, '//*[@id="errors"]'),
                (By.CSS_SELECTOR, '.alert-danger'),
                (By.CSS_SELECTOR, '#painel-erros'),
                (By.XPATH, '//div[contains(@class, "erros")]')
            ]:
                try:
                    elem = self.find_element(*selector)
                    if elem and elem.text.strip():
                        return False, elem.text.strip()
                except Exception:
                    pass
            return False, f"Credenciais inválidas ou erro ao carregar portal discente (URL: {self.driver.current_url})."

    def __str__(self) -> str:
        return "Página de Login"

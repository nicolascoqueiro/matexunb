"""Page Object representando a etapa final de confirmação de matrícula no SIGAA."""

from typing import Tuple, Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from pages.base_page import BasePage


class EnrollmentConfirmation(BasePage):
    """Encapsula a inserção final de credenciais (CPF, data de nascimento e senha) e validação da efetivação da matrícula."""

    def __init__(
        self,
        driver: WebDriver,
        cpf: str,
        date_of_birth: str = "",
        password: str = "",
        timeout: float = 10.0,
        data_nascimento: Optional[str] = None,
        senha: Optional[str] = None,
    ):
        """Inicializa a página de confirmação de matrícula.

        Args:
            driver (WebDriver): Instância ativa do WebDriver.
            cpf (str): CPF do estudante.
            date_of_birth (str): Data de nascimento DDMMAAAA.
            password (str): Senha do estudante.
            timeout (float): Limite de tempo de espera.
            data_nascimento (Optional[str]): Alias legada para date_of_birth.
            senha (Optional[str]): Alias legada para password.
        """
        super().__init__(driver, timeout)
        self.cpf: str = cpf
        self.date_of_birth: str = data_nascimento if data_nascimento is not None else date_of_birth
        self.password: str = senha if senha is not None else password

    def run(self) -> Tuple[bool, str]:
        """Executa o fluxo completo de submissão do formulário final de confirmação de matrícula.

        Returns:
            Tuple[bool, str]: Tupla (sucesso, mensagem_ou_erro).
        """
        self.wait_load_page()
        self.fill_form()
        self.submit()
        return self.verify_confirm()

    def wait_load_page(self) -> None:
        """Aguarda a presença do botão/campo de confirmação na tela."""
        self.wait_for_element(
            By.XPATH,
            "//input[contains(@id, 'btnConfirmar')] | //input[contains(@id, 'senha')] | //input[@type='password']",
        )

    def fill_form(self) -> None:
        """Verifica os campos presentes na página de confirmação e preenche o CPF, data de nascimento e senha."""
        # Preenche CPF caso o campo esteja presente na página
        try:
            cpf_input = self.find_element(By.XPATH, "//input[contains(@id, 'cpf')]")
            cpf_input.clear()
            cpf_input.send_keys(self.cpf)
        except Exception:
            pass

        # Preenche Data de Nascimento caso o campo esteja presente
        try:
            dn_input = self.find_element(
                By.XPATH, "//input[contains(@id, 'Data') or contains(@id, 'dataNascimento') or contains(@id, 'nascimento')]"
            )
            dn_input.clear()
            dn_input.send_keys(self.date_of_birth)
        except Exception:
            pass

        # Preenche a senha obrigatória
        try:
            senha_input = self.find_element(By.XPATH, "//input[contains(@id, 'senha') or @type='password']")
            senha_input.clear()
            senha_input.send_keys(self.password)
        except Exception as e:
            logger.error(f"Campo de senha não encontrado na confirmação: {e}")

    def submit(self) -> None:
        """Submete o formulário de confirmação clicando em Confirmar e aceitando alerta modal se surgir."""
        try:
            btn = self.find_element(
                By.XPATH, "//input[contains(@id, 'btnConfirmar')] | //input[contains(@value, 'Confirmar')] | //button[contains(., 'Confirmar')]"
            )
            btn.click()
        except Exception:
            btn = self.find_element(By.XPATH, "//input[contains(@id, 'btnConfirmar')]")
            self.driver.execute_script("arguments[0].click();", btn)

        try:
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import WebDriverWait
            WebDriverWait(self.driver, 5.0).until(EC.alert_is_present())
            alert = self.driver.switch_to.alert
            alert.accept()
        except Exception:
            pass

    def verify_confirm(self) -> Tuple[bool, str]:
        """Verifica se a confirmação resultou em erro exibido na tela ou em sucesso.

        Returns:
            Tuple[bool, str]: (True, "Matriculado com sucesso!") ou (False, mensagem_erro).
        """
        try:
            for error_sel in [
                (By.CSS_SELECTOR, "#painel-erros ul.erros li"),
                (By.CSS_SELECTOR, ".alert-danger"),
                (By.XPATH, "//div[contains(@class, 'erros')]//li"),
            ]:
                try:
                    erro_elem = self.find_element(*error_sel)
                    if erro_elem and erro_elem.text.strip():
                        return False, erro_elem.text.strip()
                except Exception:
                    pass

            return True, "Matriculado com sucesso!"
        except Exception:
            return True, "Matriculado com sucesso!"

    def __str__(self) -> str:
        return "Confirmação de Matrícula"

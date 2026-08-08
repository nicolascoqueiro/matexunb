"""Page Object representando o Portal do Estudante no SIGAA."""

from typing import Tuple
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
from pages.base_page import BasePage


class StudentPortal(BasePage):
    """Encapsula a navegação no menu principal do portal do aluno até a tela de Matrícula Extraordinária."""

    URL = "https://sigaa.unb.br/sigaa/portais/discente/discente.jsf"

    def __init__(self, driver: WebDriver, timeout: float = 10.0):
        """Inicializa o StudentPortal.

        Args:
            driver (WebDriver): Instância ativa do WebDriver.
            timeout (float): Limite de tempo de espera.
        """
        super().__init__(driver, timeout)

    def run(self) -> Tuple[bool, str]:
        """Executa o fluxo de navegação no portal discente.

        Returns:
            Tuple[bool, str]: Tupla (sucesso, mensagem_de_erro).
        """
        self.open_page(self.URL)
        self.wait_load_page()
        self.confirm_terms()
        self.access_menu_items()
        return self.verify_extraordinary_registration()

    def wait_load_page(self) -> None:
        """Aguarda o carregamento do menu 'Ensino' no portal."""
        self.wait_for_element(
            By.XPATH,
            "//td[contains(@class, 'ThemeOfficeMainItem') and contains(., 'Ensino')]",
        )

    def access_menu_items(self) -> None:
        """Navega pelos submenus suspensos: Ensino -> Matrícula On-Line -> Realizar Matrícula Extraordinária."""
        import time, re, logging
        from bs4 import BeautifulSoup
        log = logging.getLogger(__name__)

        # 1. Tenta extrair a ação do JSCookMenu via BeautifulSoup para acionamento direto e infalível
        try:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            menu_form = soup.find("form", id="menu:form_menu_discente")
            if menu_form and menu_form.find("script"):
                script_text = menu_form.find("script").text
                match = re.search(r"'([^']*matriculaExtraordinaria\.iniciar[^']*)'", script_text)
                if match:
                    action_val = match.group(1)
                    log.info(f"✅ BeautifulSoup extraiu ação do menu de Matrícula Extraordinária: {action_val}")
                    self.driver.execute_script('''
                        var form = document.getElementById('menu:form_menu_discente');
                        if (form && form['jscook_action']) {
                            form['jscook_action'].value = arguments[0];
                            form.submit();
                        }
                    ''', action_val)
                    time.sleep(2.5)
                    return
        except Exception as e:
            log.warning(f"Extração via BeautifulSoup para JSCookMenu falhou ({e}). Usando fallback Selenium...")

        # 2. Fallback via Selenium Hover/Click
        try:
            ensino_menu = self.wait_for_element(
                By.XPATH,
                "//td[contains(@class, 'ThemeOfficeMainItem') and contains(., 'Ensino')]",
            )
            ActionChains(self.driver).move_to_element(ensino_menu).perform()
            time.sleep(0.5)

            matricula_item = self.wait_for_element(
                By.XPATH,
                "//td[contains(@class, 'ThemeOfficeMenuFolderText') and contains(., 'Matrícula On-Line')] | //tr[contains(., 'Matrícula On-Line')]",
            )
            ActionChains(self.driver).move_to_element(matricula_item).perform()
            time.sleep(0.5)

            matricula_extra_item = self.wait_for_element(
                By.XPATH,
                "//td[contains(@class, 'ThemeOfficeMenuItemText') and contains(., 'Realizar Matrícula Extraordinária') and not(contains(., 'Férias'))] | //tr[contains(., 'Realizar Matrícula Extraordinária') and not(contains(., 'Férias'))]",
            )
            try:
                matricula_extra_item.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", matricula_extra_item)

        except Exception as ex:
            log.error(f"Erro na navegação do menu discente: {ex}")

    def access_menu_itens(self) -> None:
        """Método legado de compatibilidade para access_menu_items."""
        self.access_menu_items()

    def verify_extraordinary_registration(self) -> Tuple[bool, str]:
        """Verifica se a tela de formulário da Matrícula Extraordinária carregou com sucesso.

        Returns:
            Tuple[bool, str]: (True, "") se carregada, (False, mensagem_erro) caso contrário.
        """
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            WebDriverWait(self.driver, self.timeout).until(
                lambda d: len(d.find_elements(By.XPATH, "//input[contains(@id, 'txtCodigo')]")) > 0
                or len(d.find_elements(By.XPATH, "//input[contains(@id, 'txtNome')]")) > 0
                or "extraordinaria" in d.current_url.lower()
            )
            return True, ""
        except TimeoutException:
            return False, "Erro ao carregar a página de matrícula extraordinária."

    def __str__(self) -> str:
        return "Página do estudante"

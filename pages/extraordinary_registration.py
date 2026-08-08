"""Page Object representando a formulário de busca e seleção de turma em Matrícula Extraordinária."""

import time
import logging
from typing import Tuple, Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from pages.base_page import BasePage

log = logging.getLogger(__name__)

# Sentinel retornado quando a sessão do SIGAA expirou e é necessário re-login
SESSION_EXPIRED = "SESSION_EXPIRED"

# URLs / fragmentos que indicam que o SIGAA redirecionou para a tela de login
_LOGIN_INDICATORS = [
    "sigaa/verTelaLogin.do",
    "sigaa/portais/main.jsf",
    "sigaa/entrada.jsf",
    "login.jsf",
    "login.do",
    "verTelaLogin",
]


def _is_session_expired(driver) -> bool:
    """Verifica se o SIGAA redirecionou para a tela de autenticação (sessão expirada).

    Args:
        driver: Instância ativa do WebDriver.

    Returns:
        bool: True se a sessão expirou e o SIGAA está exibindo o login.
    """
    try:
        url = driver.current_url.lower()
        if any(indicator in url for indicator in _LOGIN_INDICATORS):
            return True
        # Verificação extra: presença do formulário de login sem o campo da matrícula
        has_login_form = len(driver.find_elements(By.ID, "username")) > 0
        has_extraordinary_form = len(driver.find_elements(By.XPATH, "//input[contains(@id, 'txtCodigo')]")) > 0
        if has_login_form and not has_extraordinary_form:
            return True
    except Exception:
        pass
    return False


class ExtraordinaryRegistration(BasePage):
    """Encapsula o preenchimento de campos de busca da turma e a seleção da turma desejada no SIGAA."""

    def __init__(
        self,
        driver: WebDriver,
        component_code: str,
        schedule_class: str,
        teacher: str,
        timeout: float = 10.0,
    ):
        """Inicializa a ExtraordinaryRegistration page.

        Args:
            driver (WebDriver): Instância ativa do WebDriver.
            component_code (str): Código da matéria (ex: "FGA0317").
            schedule_class (str): Horário da turma (ex: "24T45").
            teacher (str): Nome do docente responsável.
            timeout (float): Limite de tempo de espera.
        """
        super().__init__(driver, timeout)
        self.component_code: str = component_code
        self.schedule_class: str = schedule_class
        self.teacher: str = teacher

    def run(
        self,
        max_attempts: int = 60,
        poll_interval: float = 2.0,
        session_deadline: Optional[float] = None,
    ) -> Tuple[bool, str]:
        """Executa a busca e seleção de turma em loop na tela de Matrícula Extraordinária.

        Se a turma/vaga não for encontrada nos resultados, permanece na página atual,
        atualiza com F5 (refresh), re-preenche apenas o código do componente e tenta novamente
        até que a vaga seja encontrada ou o limite de tentativas seja atingido.

        Detecta sessão expirada de duas formas:
          - **Reativa:** verifica URL/DOM após cada F5 (caso o SIGAA já redirecionou).
          - **Proativa:** compara `time.time()` com `session_deadline` antes de cada tentativa,
            renovando a sessão antes que o timeout do SIGAA ocorra.

        Args:
            max_attempts (int): Limite máximo de tentativas (fallback caso session_deadline não
                seja informado).
            poll_interval (float): Tempo de espera em segundos entre re-tentativas.
            session_deadline (Optional[float]): Timestamp UNIX a partir do qual a sessão deve
                ser renovada proativamente. Se None, apenas a detecção reativa é usada.

        Returns:
            Tuple[bool, str]: Tupla (sucesso, mensagem_de_erro).
                              Se sessão expirou ou está prestes a expirar, retorna
                              (False, SESSION_EXPIRED).
        """
        for attempt in range(1, max_attempts + 1):
            # ─── Verificação PROATIVA de tempo de sessão ───────────────────────
            if session_deadline is not None and time.time() >= session_deadline:
                log.warning(
                    f"⏰ Sessão SIGAA prestes a expirar (tentativa {attempt}). "
                    "Renovando proativamente antes do timeout do SIGAA..."
                )
                return False, SESSION_EXPIRED

            log.info(
                f"🔄 Tentativa {attempt}/{max_attempts} | Matrícula Extraordinária | Código: {self.component_code}"
            )

            # A partir da 2ª tentativa: F5 e aguarda
            if attempt > 1:
                try:
                    self.driver.refresh()
                    time.sleep(poll_interval)
                    # Aceita alert JSF que pode aparecer após refresh
                    try:
                        alert = self.driver.switch_to.alert
                        alert.accept()
                    except Exception:
                        pass
                except Exception as e:
                    log.warning(f"Aviso no refresh da página ({e}). Prosseguindo...")

            # ─── Verifica se a sessão expirou após o refresh ───────────────────
            if _is_session_expired(self.driver):
                log.warning(
                    f"⚠️  Sessão SIGAA expirada detectada na tentativa {attempt}. "
                    "Sinalizando para renovação automática de login..."
                )
                return False, SESSION_EXPIRED

            # Preenche apenas o código da disciplina e clica em Buscar
            try:
                self.share_class()
                self.submit()
            except Exception as e:
                log.warning(f"Erro ao preencher/submeter código na tentativa {attempt}: {e}")
                # Verifica se o erro foi causado por sessão expirada
                if _is_session_expired(self.driver):
                    log.warning("⚠️  Sessão expirada confirmada após falha de preenchimento.")
                    return False, SESSION_EXPIRED
                time.sleep(poll_interval)
                continue

            # Aguarda a aparição do botão de selecionar turma
            try:
                from selenium.webdriver.support.ui import WebDriverWait
                WebDriverWait(self.driver, 4.0).until(
                    lambda d: len(
                        d.find_elements(
                            By.XPATH,
                            "/html/body/div[2]/div[2]/form/table[2]/tbody/tr[2]/td[9]/a/img | //input[contains(@id, 'selecionarTurma')] | //a[contains(@id, 'selecionarTurma')] | //img[contains(@title, 'Selecionar')]/ancestor::a | //input[contains(@value, 'Selecionar')]",
                        )
                    )
                    > 0
                )
                log.info(f"✅ VAGA/TURMA ENCONTRADA no resultado da busca na tentativa {attempt}!")
                self.select_class()
                return self.verify_extraordinary_confirmation()

            except TimeoutException:
                log.info(
                    f"⏳ Vaga para {self.component_code} não disponível na tentativa "
                    f"{attempt}/{max_attempts}. Aguardando próximo F5..."
                )

        return False, f"Vaga não encontrada após {max_attempts} tentativas na página de matrícula extraordinária."

    def share_class(self) -> None:
        """Preenche o formulário de busca utilizando APENAS o código do componente."""
        clean_code = self.component_code.strip().upper() if self.component_code else ""
        elem = self.wait_for_element(By.XPATH, "//input[contains(@id, 'txtCodigo')]")
        elem.clear()
        elem.send_keys(clean_code)

    def submit(self) -> None:
        """Submete o formulário de busca de turma."""
        elem = self.wait_for_element(By.XPATH, "//input[contains(@id, 'buscar') or @value='Buscar']")
        try:
            elem.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", elem)

    def wait_class_appear(self) -> None:
        """Aguarda o aparecimento do botão/link de seleção de turma nos resultados."""
        self.wait_for_element(
            By.XPATH,
            "/html/body/div[2]/div[2]/form/table[2]/tbody/tr[2]/td[9]/a/img | //input[contains(@id, 'selecionarTurma')] | //a[contains(@id, 'selecionarTurma')] | //img[contains(@title, 'Selecionar')]/ancestor::a | //input[contains(@value, 'Selecionar')]",
        )

    def select_class(self) -> None:
        """Clica no botão/link para selecionar a turma encontrada."""
        try:
            btn = self.find_element(By.XPATH, "/html/body/div[2]/div[2]/form/table[2]/tbody/tr[2]/td[9]/a/img")
        except Exception:
            btn = self.find_element(
                By.XPATH,
                "//input[contains(@id, 'selecionarTurma')] | //a[contains(@id, 'selecionarTurma')] | //img[contains(@title, 'Selecionar')]/ancestor::a | //input[contains(@value, 'Selecionar')]",
            )
        try:
            btn.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", btn)

    def verify_extraordinary_confirmation(self) -> Tuple[bool, str]:
        """Verifica se a tela final de confirmação de matrícula foi aberta.

        Returns:
            Tuple[bool, str]: (True, "") em sucesso ou (False, mensagem) em falha.
        """
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            WebDriverWait(self.driver, self.timeout).until(
                lambda d: len(d.find_elements(By.XPATH, "//input[contains(@id, 'btnConfirmar')]")) > 0
                or len(d.find_elements(By.XPATH, "//input[contains(@id, 'senha')]")) > 0
                or len(d.find_elements(By.XPATH, "//input[contains(@id, 'Data')]")) > 0
            )
            return True, ""
        except TimeoutException:
            return False, "Erro ao abrir componente de confirmação de matrícula."

    def __str__(self) -> str:
        return "Página de Matrícula Extraordinária"

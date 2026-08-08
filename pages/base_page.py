"""Módulo contendo a classe base para o padrão Page Object Model (POM).

Este módulo define abstrações reutilizáveis para interação com elementos Web utilizando Selenium WebDriver.
"""

from typing import List, Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class BasePage:
    """Classe base contendo métodos utilitários e encapsulamento do Selenium WebDriver."""

    def __init__(self, driver: WebDriver, timeout: float = 10.0):
        """Inicializa a página base.

        Args:
            driver (WebDriver): Instância ativa do Selenium WebDriver.
            timeout (float): Tempo máximo padrão em segundos para espera por elementos.
        """
        self.driver: WebDriver = driver
        self.timeout: float = timeout

    def open_page(self, url: str) -> None:
        """Navega para a URL informada.

        Args:
            url (str): Endereço web a ser aberto.
        """
        self.driver.get(url)

    def wait_for_element(
        self, by: str, value: str, timeout: Optional[float] = None
    ) -> WebElement:
        """Aguarda a presença de um elemento no DOM dentro do limite de tempo.

        Args:
            by (str): Estratégia de localização (ex: By.ID, By.XPATH).
            value (str): Valor do seletor.
            timeout (Optional[float]): Limite de tempo opcional. Se não informado, utiliza self.timeout.

        Returns:
            WebElement: O elemento localizado.

        Raises:
            TimeoutException: Caso o elemento não seja encontrado a tempo.
        """
        wait_time = timeout if timeout is not None else self.timeout
        return WebDriverWait(self.driver, wait_time).until(
            EC.presence_of_element_located((by, value))
        )

    def find_element(self, by: str, value: str) -> WebElement:
        """Busca um elemento no DOM.

        Args:
            by (str): Estratégia de localização (ex: By.ID, By.XPATH).
            value (str): Valor do seletor.

        Returns:
            WebElement: O elemento localizado.
        """
        return self.driver.find_element(by, value)

    def find_elements(self, by: str, value: str) -> List[WebElement]:
        """Busca múltiplos elementos no DOM.

        Args:
            by (str): Estratégia de localização.
            value (str): Valor do seletor.

        Returns:
            List[WebElement]: Lista de elementos encontrados.
        """
        return self.driver.find_elements(by, value)

    def click(self, by: str, value: str) -> None:
        """Localiza um elemento e clica nele.

        Args:
            by (str): Estratégia de localização.
            value (str): Valor do seletor.
        """
        element = self.find_element(by, value)
        element.click()

    def fill_field(self, by: str, value: str, text: str) -> None:
        """Limpa e preenche um campo de texto.

        Args:
            by (str): Estratégia de localização.
            value (str): Valor do seletor.
            text (str): Texto a ser inserido.
        """
        element = self.find_element(by, value)
        element.clear()
        element.send_keys(text)

    def confirm_terms(self, xpath: str = '//*[@id="sigaa-cookie-consent"]/button') -> bool:
        """Tenta clicar no botão de aceitação de termos/cookies caso exista.

        Args:
            xpath (str): XPath do botão de consentimento de cookies/termos.

        Returns:
            bool: True se o botão foi encontrado e clicado, False caso contrário.
        """
        try:
            btn_confirm = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            btn_confirm.click()
            return True
        except TimeoutException:
            return False

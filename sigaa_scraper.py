"""Módulo para web scraping de turmas ofertadas em tempo real no SIGAA UnB para Matrícula Extraordinária.

Realiza consulta ao vivo no portal público do SIGAA:
https://sigaa.unb.br/sigaa/public/turmas/listar.jsf

Fluxo:
1. Abre a página via Selenium headless Chrome
2. Aceita o modal de cookies ("Ciente")
3. Recarrega a página para obter um ViewState JSF fresco
4. Preenche o formulário (nível, departamento, ano, período)
5. Submete com hidden input simulando o botão "Buscar"
6. Faz parsing do HTML da tabela de resultados (table.listagem)
"""

import time
import re
import os
import logging
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Cache em memória para evitar consultas repetidas ao SIGAA no mesmo período de execução
_scrape_cache: Dict[str, List[Dict[str, str]]] = {}


def _get_selenium_driver():
    """Cria e retorna um driver Selenium Chrome headless."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-gpu')
    # Silencia logs do Chrome
    options.add_argument('--log-level=3')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])

    return webdriver.Chrome(options=options)


def _parse_schedule_text(raw_text: str) -> str:
    """Extrai apenas o código do horário (ex: '35N34 (10/08/2026 - 14/12/2026)')
    removendo o texto expandido (ex: 'Terça-feira 20:50 às 22:30')."""
    if not raw_text:
        return ''
    # Pega apenas a primeira linha que contém o código de horário
    for line in raw_text.split('\n'):
        line = line.strip()
        if line and re.match(r'^\d', line):
            return line
    return raw_text.split('\n')[0].strip()


def _parse_teacher_text(raw_text: str) -> str:
    """Limpa o texto do docente, juntando múltiplos docentes com ' / '."""
    if not raw_text:
        return ''
    parts = [p.strip() for p in raw_text.strip().split('\n') if p.strip()]
    return ' / '.join(parts)


def parse_sigaa_html_table(html_content: str) -> List[Dict[str, str]]:
    """
    Faz o Web Scraping direto do HTML da busca de turmas públicas do SIGAA UnB.
    
    Estrutura da tabela:
    - thead: 7 colunas (Código, Ano-Período, Docente, Horário, Vagas Ofertadas, Vagas Ocupadas, Local)
    - tbody: linhas agrupadas por disciplina (tr.agrupador) com 8 TDs por linha de dados:
      TD[0]=Turma, TD[1]=Ano.Período, TD[2]=Docente, TD[3]=Horário, 
      TD[4]=(vazio), TD[5]=Vagas Ofertadas, TD[6]=Vagas Ocupadas, TD[7]=Local
    - tfoot: "X turmas encontrada(s)"
    """
    if not html_content or "<table" not in html_content:
        return []

    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        turmas_div = soup.find('div', id='turmasAbertas')
        table = turmas_div.find('table', class_='listagem') if turmas_div else soup.find('table', class_='listagem')
        if not table:
            table = soup.find('table')
        if not table:
            return []

        # Log do tfoot
        tfoot = table.find('tfoot')
        if tfoot:
            tfoot_text = tfoot.get_text().strip()
            if tfoot_text:
                logger.info(f"SIGAA tfoot: '{tfoot_text}'")

        classes = []
        current_code = ''
        current_name = ''

        for tr in table.find_all('tr'):
            td_class = tr.get('class', [])

            # Linha agrupadora (nome da disciplina)
            if 'agrupador' in td_class:
                text = tr.get_text().strip()
                if ' - ' in text:
                    parts = text.split(' - ', 1)
                    current_code = parts[0].strip()
                    current_name = parts[1].strip()
                continue

            # Pular tfoot
            if tr.find_parent('tfoot'):
                continue

            tds = tr.find_all('td')

            # Linhas de dados têm 8 TDs
            if len(tds) >= 8:
                turma = tds[0].get_text().strip()
                ano_periodo = tds[1].get_text().strip()
                teacher = _parse_teacher_text(tds[2].get_text())
                schedule = _parse_schedule_text(tds[3].get_text())
                # TD[4] é vazio (separador)
                vagas = tds[5].get_text().strip()
                matriculados = tds[6].get_text().strip()
                local_str = tds[7].get_text().strip()

                if turma and turma not in ('Turma', 'Código'):
                    p_ano, p_periodo = '2026', '2'
                    if '.' in ano_periodo:
                        parts = ano_periodo.split('.')
                        p_ano = parts[0].strip()
                        p_periodo = parts[1].strip()

                    classes.append({
                        'code': current_code,
                        'turma': turma,
                        'name': current_name,
                        'schedule': schedule,
                        'teacher': teacher,
                        'vagas': vagas or '0',
                        'matriculados': matriculados or '0',
                        'local': local_str or 'A definir',
                        'ano': p_ano,
                        'periodo': p_periodo
                    })

            # Fallback para tabelas com 7 TDs (HTML fornecido manualmente)
            elif len(tds) == 7:
                turma = tds[0].get_text().strip()
                ano_periodo = tds[1].get_text().strip()
                teacher = _parse_teacher_text(tds[2].get_text())
                schedule = _parse_schedule_text(tds[3].get_text())
                vagas = tds[4].get_text().strip()
                matriculados = tds[5].get_text().strip()
                local_str = tds[6].get_text().strip()

                if turma and turma not in ('Turma', 'Código'):
                    p_ano, p_periodo = '2026', '2'
                    if '.' in ano_periodo:
                        parts = ano_periodo.split('.')
                        p_ano = parts[0].strip()
                        p_periodo = parts[1].strip()

                    classes.append({
                        'code': current_code,
                        'turma': turma,
                        'name': current_name,
                        'schedule': schedule,
                        'teacher': teacher,
                        'vagas': vagas or '0',
                        'matriculados': matriculados or '0',
                        'local': local_str or 'A definir',
                        'ano': p_ano,
                        'periodo': p_periodo
                    })

        return classes
    except Exception as e:
        logger.error(f"Erro ao fazer parsing do HTML do SIGAA: {e}")
        return []


def fetch_live_sigaa_selenium(
    depto_code: str,
    nivel: str = "G",
    ano: str = "2026",
    periodo: str = "2"
) -> List[Dict[str, str]]:
    """
    Realiza consulta AO VIVO no portal público do SIGAA UnB via Selenium headless.
    
    URL: https://sigaa.unb.br/sigaa/public/turmas/listar.jsf
    
    Fluxo:
    1. GET na página -> aceita cookies (botão "Ciente")
    2. Recarrega a página para ViewState JSF fresco
    3. Preenche formulário e submete com hidden input
    4. Faz parsing da tabela de resultados
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import Select

    url = 'https://sigaa.unb.br/sigaa/public/turmas/listar.jsf'

    driver = None
    try:
        driver = _get_selenium_driver()

        # 1. Carregar página e aceitar cookies
        logger.info(f"Conectando ao SIGAA UnB para depto {depto_code}...")
        driver.get(url)
        time.sleep(2)

        try:
            ciente_btn = driver.find_element(By.CSS_SELECTOR, '#sigaa-cookie-consent button.btn-primary')
            ciente_btn.click()
            time.sleep(1)
            logger.debug("Cookie de consentimento aceito (Ciente)")
        except Exception:
            pass

        # 2. Recarregar para ViewState fresco (essencial para JSF)
        driver.get(url)
        time.sleep(2)

        # 3. Preencher formulário
        try:
            Select(driver.find_element(By.NAME, 'formTurma:inputNivel')).select_by_value(nivel)
        except Exception:
            pass
        time.sleep(0.5)

        Select(driver.find_element(By.NAME, 'formTurma:inputDepto')).select_by_value(str(depto_code))
        time.sleep(0.5)

        # Setar ano
        ano_input = driver.find_element(By.NAME, 'formTurma:inputAno')
        ano_input.clear()
        ano_input.send_keys(str(ano))

        # Setar período
        try:
            Select(driver.find_element(By.NAME, 'formTurma:inputPeriodo')).select_by_value(str(periodo))
        except Exception:
            pass
        time.sleep(0.5)

        # 4. Submeter — injetar hidden input com nome do botão "Buscar" e fazer form.submit()
        btn_name = driver.find_element(By.XPATH, '//input[@value="Buscar"]').get_attribute('name')
        driver.execute_script('''
            var form = document.getElementById('formTurma');
            var hidden = document.createElement('input');
            hidden.type = 'hidden';
            hidden.name = arguments[0];
            hidden.value = 'Buscar';
            form.appendChild(hidden);
            form.submit();
        ''', btn_name)
        time.sleep(5)

        # 5. Tratar alerta se surgir
        try:
            alert = driver.switch_to.alert
            logger.warning(f"SIGAA alert: {alert.text}")
            alert.accept()
            time.sleep(1)
            return []
        except Exception:
            pass

        # 6. Extrair HTML e fazer parsing
        html = driver.page_source
        classes = parse_sigaa_html_table(html)

        if classes:
            logger.info(f"✅ SIGAA ao vivo: {len(classes)} turmas reais extraídas para depto {depto_code}")
        else:
            logger.info(f"SIGAA ao vivo: 0 turmas encontradas para depto {depto_code}")

        return classes

    except Exception as e:
        logger.error(f"Erro no scraping Selenium para depto {depto_code}: {e}")
        return []
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def fetch_offered_classes(
    depto_code: str = "673",
    nivel: str = "G",
    ano: str = "",
    periodo: str = "",
    search: str = "",
    headless: bool = True,
    html_content: str = "",
) -> List[Dict[str, str]]:
    """
    Busca turmas ofertadas para um departamento.
    
    Prioridade:
    1. HTML fornecido diretamente (parse_sigaa_html_table)
    2. Cache em memória (evita consultas repetidas)
    3. Scraping ao vivo via Selenium no SIGAA UnB
    """
    logger.info(f"Buscando turmas ofertadas (Depto: {depto_code}, Ano: {ano}, Período: {periodo}, Search: '{search}')...")

    req_ano = ano if ano else "2026"
    req_periodo = periodo if periodo else "2"
    depto_str = str(depto_code).strip()

    # 1. Se foi fornecido conteúdo HTML direto
    if html_content:
        scraped_from_html = parse_sigaa_html_table(html_content)
        if scraped_from_html:
            return scraped_from_html

    # 2. Verificar cache
    cache_key = f"{depto_str}_{nivel}_{req_ano}_{req_periodo}"
    if cache_key in _scrape_cache:
        base_classes = _scrape_cache[cache_key]
        logger.info(f"Cache hit: {len(base_classes)} turmas para {cache_key}")
    else:
        # 3. Scraping ao vivo via Selenium
        base_classes = fetch_live_sigaa_selenium(depto_str, nivel, req_ano, req_periodo)
        # Salvar no cache
        _scrape_cache[cache_key] = base_classes

    # Aplicar filtro de busca
    results = base_classes
    if search:
        search_term = search.strip().lower()
        filtered = [
            c for c in base_classes
            if search_term in c.get("code", "").lower()
            or search_term in c.get("name", "").lower()
            or search_term in c.get("teacher", "").lower()
        ]
        if filtered:
            results = filtered

    # Garantir ano/período correto na resposta
    final_list = []
    for item in results:
        item_copy = dict(item)
        item_copy["ano"] = req_ano
        item_copy["periodo"] = req_periodo
        final_list.append(item_copy)

    return final_list

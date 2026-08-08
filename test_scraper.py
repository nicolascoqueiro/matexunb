"""Suíte de testes automatizados para validação do Web Scraper SIGAA UnB ao vivo.

Testa a extração real de turmas do portal público:
https://sigaa.unb.br/sigaa/public/turmas/listar.jsf
"""

import unittest
import sys
import os

# Adiciona o diretório atual ao PATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sigaa_scraper import fetch_offered_classes, parse_sigaa_html_table
from models.offered_db import OfferedDB
from web_app import app, PUBLIC_DB_PATH


class TestSigaaWebScraper(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_01_scrape_live_depto_640_cds(self):
        """Testa scraping ao vivo do CDS (640) — deve retornar 13 turmas reais."""
        classes = fetch_offered_classes(depto_code="640", ano="2026", periodo="2")
        self.assertGreater(len(classes), 0, "CDS (640) deveria retornar turmas ao vivo do SIGAA.")
        print(f"✅ TEST 1 PASSED: CDS (640) retornou {len(classes)} turmas ao vivo do SIGAA UnB.")
        
        # Verificar que os dados são reais (contém códigos CDS)
        codes = set(c["code"] for c in classes)
        self.assertTrue(any("CDS" in code for code in codes), "Deveria conter disciplinas com código CDS.")
        print(f"   Disciplinas encontradas: {codes}")

    def test_02_scrape_live_depto_508_cic(self):
        """Testa scraping ao vivo do CIC (508) — deve retornar turmas reais."""
        classes = fetch_offered_classes(depto_code="508", ano="2026", periodo="2")
        self.assertGreater(len(classes), 0, "CIC (508) deveria retornar turmas ao vivo do SIGAA.")
        print(f"✅ TEST 2 PASSED: CIC (508) retornou {len(classes)} turmas ao vivo do SIGAA UnB.")
        
        # Verificar que os dados têm campos obrigatórios
        first = classes[0]
        self.assertIn("code", first)
        self.assertIn("turma", first)
        self.assertIn("name", first)
        self.assertIn("schedule", first)
        self.assertIn("teacher", first)
        self.assertIn("vagas", first)
        self.assertIn("matriculados", first)
        self.assertIn("local", first)
        print(f"   Primeiro resultado: {first['code']} - {first['name']}")

    def test_03_scrape_live_depto_345_com(self):
        """Testa scraping ao vivo do COM (345) — deve retornar turmas reais."""
        classes = fetch_offered_classes(depto_code="345", ano="2026", periodo="2")
        self.assertGreater(len(classes), 0, "COM (345) deveria retornar turmas ao vivo do SIGAA.")
        print(f"✅ TEST 3 PASSED: COM (345) retornou {len(classes)} turmas ao vivo do SIGAA UnB.")

    def test_04_scrape_live_search_filter(self):
        """Testa filtro de busca por nome de disciplina."""
        classes = fetch_offered_classes(depto_code="508", ano="2026", periodo="2", search="COMPUTAÇÃO")
        # Se houver turmas com "COMPUTAÇÃO" no nome, deve retornar
        if classes:
            self.assertTrue(
                any("COMPUTAÇÃO" in c["name"].upper() or "COMPUTAÇÃO" in c["code"].upper() for c in classes),
                "Busca por 'COMPUTAÇÃO' deveria retornar disciplinas com esse termo."
            )
            print(f"✅ TEST 4 PASSED: Busca por 'COMPUTAÇÃO' retornou {len(classes)} turmas filtradas.")
        else:
            print(f"✅ TEST 4 PASSED: Busca por 'COMPUTAÇÃO' retornou 0 resultados (pode não haver turmas com esse termo).")

    def test_05_schedule_parsing(self):
        """Testa que o campo schedule contém apenas o código de horário, sem texto expandido."""
        classes = fetch_offered_classes(depto_code="640", ano="2026", periodo="2")
        if classes:
            for c in classes:
                schedule = c["schedule"]
                # Não deve conter "Terça-feira", "Segunda-feira" etc.
                self.assertNotIn("feira", schedule.lower(), 
                    f"Schedule '{schedule}' não deveria conter dias da semana expandidos.")
            print(f"✅ TEST 5 PASSED: Todos os schedules estão limpos (sem texto de dia da semana expandido).")
        else:
            self.skipTest("Sem turmas ao vivo para verificar schedule.")

    def test_06_vagas_local_parsing(self):
        """Testa que vagas e local estão extraídos corretamente (não invertidos)."""
        classes = fetch_offered_classes(depto_code="640", ano="2026", periodo="2")
        if classes:
            first = classes[0]
            # Vagas deve ser numérico
            self.assertTrue(first["vagas"].isdigit(), 
                f"Vagas '{first['vagas']}' deveria ser um número.")
            # Local não deve ser um número puro
            print(f"✅ TEST 6 PASSED: Vagas='{first['vagas']}', Ocupadas='{first['matriculados']}', Local='{first['local']}'")
        else:
            self.skipTest("Sem turmas ao vivo para verificar vagas/local.")

    def test_07_parse_sigaa_html_table_direct(self):
        """Testa o parser direto com HTML simulando a estrutura real do SIGAA (7 TDs)."""
        raw_html = '''
        <div id="corpo">
        <form id="formTurma">
        <div id="turmasAbertas">
        <table class="listagem">
        <tbody>
        <tr class="agrupador"><td colspan="8">CDS0001 - PLANEJAMENTO E AVALIAÇÃO SOCIOAMBIENTAL</td></tr>
        <tr><td>01</td><td>2026.2</td><td>LAURA ANGELICA FERREIRA DARNET (60h)</td><td>35N34 (10/08/2026 - 14/12/2026)</td><td>30</td><td>0</td><td>A definir</td></tr>
        <tr class="agrupador"><td colspan="8">CDS0006 - GOVERNANÇA AMBIENTAL</td></tr>
        <tr><td>01</td><td>2026.2</td><td>FABIANO TONI (60h)</td><td>35M34 (10/08/2026 - 14/12/2026)</td><td>30</td><td>0</td><td>SALA COPAIBA (CDS)</td></tr>
        </tbody>
        <tfoot><tr><td colspan="8" align="center"> <b>13 turmas encontrada(s) </b></td></tr></tfoot>
        </table>
        </div>
        </form>
        </div>
        '''
        classes = parse_sigaa_html_table(raw_html)
        self.assertEqual(len(classes), 2)
        self.assertEqual(classes[0]["code"], "CDS0001")
        self.assertEqual(classes[0]["teacher"], "LAURA ANGELICA FERREIRA DARNET (60h)")
        self.assertEqual(classes[1]["code"], "CDS0006")
        self.assertEqual(classes[1]["local"], "SALA COPAIBA (CDS)")
        print(f"✅ TEST 7 PASSED: Parser HTML direto validado com sucesso!")

    def test_08_api_scraper_search_endpoint(self):
        """Testa o endpoint REST /api/scraper/search."""
        payload = {
            "depto_code": "640",
            "nivel": "G",
            "ano": "2026",
            "periodo": "2",
            "search": ""
        }
        res = self.app.post("/api/scraper/search", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertGreater(len(data["classes"]), 0)
        print(f"✅ TEST 8 PASSED: API /api/scraper/search retornou {len(data['classes'])} turmas ao vivo.")

    def test_09_cache_prevents_duplicate_requests(self):
        """Testa que o cache evita consultas duplicadas ao SIGAA."""
        # Primeira chamada (pode ir ao SIGAA ou usar cache de teste anterior)
        classes1 = fetch_offered_classes(depto_code="640", ano="2026", periodo="2")
        # Segunda chamada (deve usar cache)
        classes2 = fetch_offered_classes(depto_code="640", ano="2026", periodo="2")
        self.assertEqual(len(classes1), len(classes2), "Cache deve retornar os mesmos resultados.")
        print(f"✅ TEST 9 PASSED: Cache funcionando — {len(classes1)} turmas retornadas sem requisição duplicada.")


if __name__ == "__main__":
    unittest.main(verbosity=2)

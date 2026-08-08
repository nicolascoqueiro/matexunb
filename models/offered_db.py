"""Módulo de persistência no Banco de Dados (public/db.json) para as turmas ofertadas do SIGAA."""

import json
import os
import time
from typing import List, Dict, Any, Optional


class OfferedDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        dir_name = os.path.dirname(self.db_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        if not os.path.exists(self.db_path):
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump({"classes": [], "offered_classes": []}, f, indent=4)

    def _load_data(self) -> Dict[str, Any]:
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "offered_classes" not in data:
                    data["offered_classes"] = []
                return data
        except Exception:
            return {"classes": [], "offered_classes": []}

    def _save_data(self, data: Dict[str, Any]):
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def get_offered_classes(
        self,
        depto_code: str,
        ano: str = "2026",
        periodo: str = "1",
        search: str = ""
    ) -> List[Dict[str, str]]:
        """Busca turmas ofertadas já salvas no banco de dados local."""
        data = self._load_data()
        all_offered = data.get("offered_classes", [])

        # Filtra por departamento e/ou ano/período
        filtered = []
        for item in all_offered:
            match_depto = not depto_code or item.get("depto_code") == depto_code
            match_ano = not ano or item.get("ano") == ano
            match_periodo = not periodo or item.get("periodo") == periodo

            if match_depto and match_ano and match_periodo:
                filtered.append(item)

        # Se houver termo de busca, filtra por código, nome ou professor
        if search:
            s_lower = search.strip().lower()
            matching_search = []
            for item in filtered:
                if (
                    s_lower in item.get("code", "").lower()
                    or s_lower in item.get("name", "").lower()
                    or s_lower in item.get("teacher", "").lower()
                ):
                    matching_search.append(item)
            return matching_search

        return filtered

    def save_offered_classes(
        self,
        depto_code: str,
        ano: str,
        periodo: str,
        classes: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Salva a lista de turmas raspadas no banco de dados (public/db.json), substituindo ou adicionando."""
        data = self._load_data()
        current_offered = data.get("offered_classes", [])

        # Remove entradas antigas da mesma combinação de depto/ano/periodo para atualizar
        updated_list = [
            item for item in current_offered
            if not (
                item.get("depto_code") == depto_code
                and item.get("ano") == ano
                and item.get("periodo") == periodo
            )
        ]

        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ")

        for c in classes:
            item_entry = {
                "code": c.get("code", ""),
                "turma": c.get("turma", "01"),
                "name": c.get("name", ""),
                "schedule": c.get("schedule", ""),
                "teacher": c.get("teacher", ""),
                "vagas": c.get("vagas", "80"),
                "matriculados": c.get("matriculados", "0"),
                "local": c.get("local", f"FCTE - I9/I10"),
                "depto_code": depto_code,
                "ano": ano if ano else c.get("ano", "2026"),
                "periodo": periodo if periodo else c.get("periodo", "2"),
                "saved_at": timestamp
            }
            updated_list.append(item_entry)

        data["offered_classes"] = updated_list
        self._save_data(data)
        return classes

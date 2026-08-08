"""Módulo responsável pela manipulação da base de dados pública JSON (db.json)."""

import json
import logging
from typing import List
from models.school_class import SchoolClass

logger = logging.getLogger(__name__)


class DB:
    """Gerencia a leitura e escrita de informações públicas (turmas e dados não sensíveis dos estudantes) em arquivo JSON."""

    def __init__(self, filename: str):
        """Inicializa o repositório de dados públicos.

        Args:
            filename (str): Caminho para o arquivo JSON público (ex: "public/db.json").
        """
        self.filename: str = filename

    def load(self) -> List[SchoolClass]:
        """Carrega a lista de turmas e alunos a partir do arquivo JSON público.

        Returns:
            List[SchoolClass]: Lista de objetos SchoolClass deserializados. Retorna lista vazia em caso de arquivo ausente ou erro.
        """
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                data = json.load(f)
            classes = [SchoolClass.from_dict(item) for item in data.get("classes", [])]
            return classes
        except FileNotFoundError:
            logger.warning(f"Arquivo público '{self.filename}' não encontrado. Retornando lista vazia.")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON do arquivo '{self.filename}': {e}")
            return []

    def save(self, classes: List[SchoolClass]) -> None:
        """Salva a lista de turmas e seus dados públicos no arquivo JSON.

        Args:
            classes (List[SchoolClass]): Lista de turmas a ser persistida.
        """
        data = {"classes": [c.to_dict() for c in classes]}
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

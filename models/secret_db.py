"""Módulo responsável pela manipulação da base de dados privada JSON (secret/db.json)."""

import json
import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SecretDB:
    """Gerencia a leitura e escrita de dados sensíveis dos estudantes (CPF, data de nascimento, senha)."""

    def __init__(self, secret_filename: str):
        """Inicializa o repositório de dados sensíveis.

        Args:
            secret_filename (str): Caminho para o arquivo JSON secreto (ex: "secret/db.json").
        """
        self.secret_filename: str = secret_filename

    def _load_secret_data(self) -> Dict[str, Any]:
        """Lê o arquivo de dados sensíveis e retorna o dicionário bruto.

        Returns:
            Dict[str, Any]: Dicionário contendo a lista "students" com credenciais.
        """
        try:
            with open(self.secret_filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Arquivo secreto '{self.secret_filename}' não encontrado.")
            return {"students": []}
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON secreto '{self.secret_filename}': {e}")
            return {"students": []}

    def _save_secret_data(self, data: Dict[str, Any]) -> None:
        """Salva o dicionário de dados sensíveis no arquivo JSON em disco.

        Args:
            data (Dict[str, Any]): Dicionário com a estrutura de dados sensíveis.
        """
        dir_name = os.path.dirname(self.secret_filename)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(self.secret_filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def get_student_sensitive(self, registration: str) -> Optional[Dict[str, str]]:
        """Busca e retorna os dados sensíveis de um aluno filtrado pela matrícula.

        Args:
            registration (str): Matrícula acadêmica do aluno.

        Returns:
            Optional[Dict[str, str]]: Dicionário com keys ('cpf', 'date_of_birth', 'password') ou None se não encontrado.
        """
        data = self._load_secret_data()
        for student in data.get("students", []):
            if student.get("registration") == registration:
                return student
        return None

    def save_student_sensitive(
        self, registration: str, cpf: str, date_of_birth: str, password: str, name: str = ""
    ) -> None:
        """Atualiza ou insere os dados sensíveis de um estudante pela matrícula.

        Args:
            registration (str): Matrícula do estudante.
            cpf (str): CPF do estudante.
            date_of_birth (str): Data de nascimento.
            password (str): Senha de acesso.
            name (str): Nome do estudante.
        """
        data = self._load_secret_data()
        students = data.setdefault("students", [])
        found = False

        for student in students:
            if (registration and student.get("registration") == registration) or (cpf and student.get("cpf") == cpf):
                if registration:
                    student["registration"] = registration
                if cpf:
                    student["cpf"] = cpf
                student["date_of_birth"] = date_of_birth
                student["password"] = password
                if name:
                    student["name"] = name
                found = True
                break

        if not found:
            entry = {
                "registration": registration,
                "cpf": cpf,
                "date_of_birth": date_of_birth,
                "password": password,
            }
            if name:
                entry["name"] = name
            students.append(entry)

        self._save_secret_data(data)

"""Módulo de representação do modelo de Aluno (Student)."""

from typing import Dict, Any


class Student:
    """Representa um aluno cadastrado no sistema com seus dados públicos e sensíveis."""

    def __init__(
        self,
        name: str,
        cpf: str,
        registration: str,
        date_of_birth: str,
        password: str,
        get_enrolled: bool,
        error: str = "",
    ):
        """Inicializa um objeto Student.

        Args:
            name (str): Nome completo do estudante.
            cpf (str): Cadastro de Pessoa Física (dado sensível).
            registration (str): Matrícula acadêmica do estudante.
            date_of_birth (str): Data de nascimento DDMMAAAA (dado sensível).
            password (str): Senha de acesso ao sistema (dado sensível).
            get_enrolled (bool): Indica se a matrícula foi realizada com sucesso.
            error (str, optional): Mensagem de erro caso a tentativa de matrícula tenha falhado.
        """
        self.name: str = name
        self.cpf: str = cpf
        self.registration: str = registration
        self.date_of_birth: str = date_of_birth
        self.password: str = password
        self.get_enrolled: bool = get_enrolled
        self.error: str = error

    def to_dict_public(self) -> Dict[str, Any]:
        """Retorna um dicionário contendo apenas informações públicas (não sensíveis).

        Returns:
            Dict[str, Any]: Dicionário formatado para armazenamento em db.json.
        """
        return {
            "name": self.name,
            "registration": self.registration,
            "get_enrolled": self.get_enrolled,
            "error": self.error,
        }

    def to_dict_sensitive(self) -> Dict[str, str]:
        """Retorna um dicionário contendo apenas informações sensíveis.

        Returns:
            Dict[str, str]: Dicionário formatado para armazenamento no arquivo secreto secret/db.json.
        """
        return {
            "registration": self.registration,
            "cpf": self.cpf,
            "date_of_birth": self.date_of_birth,
            "password": self.password,
        }

    @classmethod
    def from_dict_public(cls, data: Dict[str, Any]) -> "Student":
        """Instancia um Student a partir de um dicionário com dados públicos.

        Nota: Dados sensíveis (cpf, data de nascimento, senha) iniciam vazios e
        devem ser preenchidos posteriormente via SecretDB.

        Args:
            data (Dict[str, Any]): Dicionário vindo do repositório público db.json.

        Returns:
            Student: Instância de Student pré-inicializada.
        """
        return cls(
            name=data.get("name", ""),
            cpf="",
            registration=data.get("registration", ""),
            date_of_birth="",
            password="",
            get_enrolled=data.get("get_enrolled", False),
            error=data.get("error", ""),
        )

    def __str__(self) -> str:
        return f"{self.name} (Matrícula: {self.registration})"

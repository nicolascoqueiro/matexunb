"""Módulo de representação do modelo de Turma Disciplinar (SchoolClass)."""

from typing import List, Dict, Any, Optional
from models.students import Student


class SchoolClass:
    """Representa uma turma ofertada com código da disciplina, departamento, nível, ano, período, horário, docente e lista de alunos."""

    def __init__(
        self,
        code: str,
        schedule_class: str,
        teacher: str,
        depto_code: str = "673",
        nivel: str = "G",
        ano: str = "2026",
        periodo: str = "2",
        students: Optional[List[Student]] = None,
    ):
        """Inicializa um objeto SchoolClass.

        Args:
            code (str): Código da disciplina (ex: "FGA0109").
            schedule_class (str): Horário da turma (ex: "35T23").
            teacher (str): Nome do docente responsável.
            depto_code (str): Código do departamento/unidade no SIGAA (ex: "673", "508").
            nivel (str): Nível de ensino ('G' = Graduação, 'S' = Stricto Sensu, etc.).
            ano (str): Ano letivo (ex: "2026").
            periodo (str): Período/Semestre (ex: "1" ou "2").
            students (Optional[List[Student]]): Lista de instâncias de Student associados a esta turma.
        """
        self.code: str = code
        self.schedule_class: str = schedule_class
        self.teacher: str = teacher
        self.depto_code: str = depto_code
        self.nivel: str = nivel
        self.ano: str = ano
        self.periodo: str = periodo
        self.students: List[Student] = students if students is not None else []

    def to_dict(self) -> Dict[str, Any]:
        """Converte o objeto SchoolClass em um dicionário serializável para JSON.

        Returns:
            Dict[str, Any]: Dicionário contendo os dados da turma e dos estudantes (dados públicos).
        """
        return {
            "code": self.code,
            "schedule_class": self.schedule_class,
            "teacher": self.teacher,
            "depto_code": self.depto_code,
            "nivel": self.nivel,
            "ano": self.ano,
            "periodo": self.periodo,
            "students": [student.to_dict_public() for student in self.students],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SchoolClass":
        """Cria uma instância de SchoolClass a partir de um dicionário contendo os dados lidos do JSON público.

        Args:
            data (Dict[str, Any]): Dicionário com informações da turma.

        Returns:
            SchoolClass: Instância de turma populada com sua lista de estudantes.
        """
        students_data = data.get("students", [])
        students = [Student.from_dict_public(s) for s in students_data]
        return cls(
            code=data.get("code", ""),
            schedule_class=data.get("schedule_class", ""),
            teacher=data.get("teacher", ""),
            depto_code=data.get("depto_code", "673"),
            nivel=data.get("nivel", "G"),
            ano=data.get("ano", "2026"),
            periodo=data.get("periodo") or "2",
            students=students,
        )

    def __str__(self) -> str:
        return f"{self.code} ({self.depto_code}) - {self.schedule_class} [{self.ano}/{self.periodo}] - {self.teacher}"

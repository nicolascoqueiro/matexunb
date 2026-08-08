"""Módulo de configuração e integração entre bases de dados públicas e privadas."""

import logging
from typing import List
from models.db import DB
from models.secret_db import SecretDB
from models.school_class import SchoolClass

logger = logging.getLogger(__name__)


def load_all_data(db_file: str, secret_file: str) -> List[SchoolClass]:
    """Carrega as turmas do arquivo público e mescla as credenciais sensíveis dos alunos do arquivo secreto.

    Args:
        db_file (str): Caminho do arquivo JSON público (ex: "public/db.json").
        secret_file (str): Caminho do arquivo JSON secreto (ex: "secret/db.json").

    Returns:
        List[SchoolClass]: Lista de turmas populadas com objetos Student completos (públicos e sensíveis).
    """
    db = DB(db_file)
    classes = db.load()

    secret_db = SecretDB(secret_file)
    secret_data = secret_db._load_secret_data()
    secret_students = secret_data.get("students", [])

    for school_class in classes:
        if not school_class.students and secret_students:
            from models.students import Student
            for s_info in secret_students:
                st = Student(
                    name=s_info.get("name") or f"Aluno ({s_info.get('registration')})",
                    cpf=s_info.get("cpf", ""),
                    registration=s_info.get("registration", ""),
                    date_of_birth=s_info.get("date_of_birth", ""),
                    password=s_info.get("password", ""),
                    get_enrolled=False,
                )
                school_class.students.append(st)

        for student in school_class.students:
            sensitive_data = secret_db.get_student_sensitive(student.registration)
            if sensitive_data:
                student.cpf = sensitive_data.get("cpf", "")
                student.date_of_birth = sensitive_data.get("date_of_birth", "")
                student.password = sensitive_data.get("password", "")
                if not student.name:
                    student.name = sensitive_data.get("name", "")
            else:
                logger.warning(
                    f"Credenciais sensíveis não encontradas no SecretDB para a matrícula {student.registration}."
                )

    return classes


def save_all_data(classes: List[SchoolClass], db_file: str, secret_file: str) -> None:
    """Salva os dados públicos das turmas no arquivo JSON público e os dados sensíveis no arquivo JSON secreto.

    Args:
        classes (List[SchoolClass]): Lista de turmas atualizadas.
        db_file (str): Caminho do arquivo JSON público.
        secret_file (str): Caminho do arquivo JSON secreto.
    """
    db = DB(db_file)
    db.save(classes)

    secret_db = SecretDB(secret_file)
    for school_class in classes:
        for student in school_class.students:
            secret_db.save_student_sensitive(
                registration=student.registration,
                cpf=student.cpf,
                date_of_birth=student.date_of_birth,
                password=student.password,
            )

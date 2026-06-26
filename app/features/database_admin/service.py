from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import psycopg


@dataclass(frozen=True)
class OperationResult:
    status: str
    message: str


def build_connection_parameters(config: dict[str, Any], password: str) -> dict[str, Any]:
    return {
        "host": str(config.get("host") or "").strip(),
        "port": int(config.get("port") or 5432),
        "dbname": str(config.get("database_name") or "").strip(),
        "user": str(config.get("username") or "").strip(),
        "password": password,
        "sslmode": str(config.get("ssl_mode") or "prefer").strip() or "prefer",
        "connect_timeout": 5,
    }


def safe_database_error_message(error: Exception) -> str:
    text = str(error).casefold()
    if "timeout" in text or "connect" in text or "could not" in text or "refused" in text:
        return "Servidor não encontrado ou porta indisponível."
    if "password" in text or "auth" in text or "senha" in text:
        return "Falha de autenticação no banco de dados."
    if "does not exist" in text or "não existe" in text or "unknown database" in text:
        return "Banco informado não existe."
    if "permission" in text or "permiss" in text or "privilege" in text:
        return "Permissão insuficiente para executar esta operação."
    return "Falha ao conectar ou preparar o banco de dados."


class DatabaseAdminService:
    def __init__(self, connector: Callable[..., Any] | None = None):
        self.connector = connector or psycopg.connect

    def test_connection(self, config: dict[str, Any], password: str) -> OperationResult:
        try:
            with self.connector(**build_connection_parameters(config, password)) as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception as exc:
            return OperationResult("error", safe_database_error_message(exc))
        return OperationResult("success", "Conexão realizada com sucesso.")

    def prepare_environment(self, config: dict[str, Any], password: str) -> OperationResult:
        try:
            with self.connector(**build_connection_parameters(config, password)) as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT 1")
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sist_ionm_schema_status (
                        id INTEGER PRIMARY KEY,
                        version TEXT NOT NULL,
                        status TEXT NOT NULL,
                        prepared_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """,
                )
                cursor.execute(
                    """
                    INSERT INTO sist_ionm_schema_status(id, version, status)
                    VALUES(1, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        version=EXCLUDED.version,
                        status=EXCLUDED.status,
                        prepared_at=CURRENT_TIMESTAMP
                    """,
                    ("2026-06-26.initial", "prepared"),
                )
                connection.commit()
        except Exception as exc:
            return OperationResult("error", safe_database_error_message(exc))
        return OperationResult("success", "Ambiente PostgreSQL preparado para migração/cutover.")

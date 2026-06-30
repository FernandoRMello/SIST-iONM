import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from app.features.database_admin.security import (
    decrypt_database_password,
    encrypt_database_password,
    password_status,
)


class DatabaseSettingsRepository:
    def __init__(self, database_path: Path | str):
        self.database_path = Path(database_path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def init_schema(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS database_connections (
                    id INTEGER PRIMARY KEY CHECK (id=1),
                    name TEXT,
                    engine TEXT DEFAULT 'postgresql',
                    host TEXT,
                    port INTEGER DEFAULT 5432,
                    database_name TEXT,
                    username TEXT,
                    password_encrypted TEXT,
                    ssl_mode TEXT DEFAULT 'prefer',
                    notes TEXT,
                    status TEXT DEFAULT 'Não configurado',
                    is_active_candidate TEXT DEFAULT 'Não',
                    last_test_status TEXT,
                    last_test_message TEXT,
                    last_test_at TEXT,
                    last_prepare_status TEXT,
                    last_prepare_message TEXT,
                    last_prepare_at TEXT,
                    updated_by_user_id INTEGER,
                    created_at TEXT,
                    updated_at TEXT
                )
                """,
            )
            connection.commit()

    def get_config(self) -> dict[str, Any]:
        self.init_schema()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM database_connections WHERE id=1",
            ).fetchone()
        if row:
            return dict(row)
        return {
            "id": 1,
            "name": "",
            "engine": "postgresql",
            "host": "",
            "port": 5432,
            "database_name": "",
            "username": "",
            "password_encrypted": "",
            "ssl_mode": "prefer",
            "notes": "",
            "status": "Não configurado",
            "is_active_candidate": "Não",
            "last_test_status": "",
            "last_test_message": "",
            "last_test_at": "",
            "last_prepare_status": "",
            "last_prepare_message": "",
            "last_prepare_at": "",
            "updated_by_user_id": None,
            "created_at": "",
            "updated_at": "",
        }

    def get_config_for_view(self) -> dict[str, Any]:
        config = self.get_config()
        config.pop("password_encrypted", None)
        config["password_status"] = password_status(self.get_config().get("password_encrypted"))
        return config

    def get_password(self, *, master_key: str) -> str:
        return decrypt_database_password(
            str(self.get_config().get("password_encrypted") or ""),
            master_key,
        )

    def save_config(
        self,
        *,
        name: str,
        engine: str,
        host: str,
        port: int,
        database_name: str,
        username: str,
        password: str,
        ssl_mode: str,
        notes: str,
        updated_by_user_id: int,
        master_key: str,
    ) -> None:
        self.init_schema()
        current = self.get_config()
        encrypted_password = (
            encrypt_database_password(password, master_key)
            if password
            else str(current.get("password_encrypted") or "")
        )
        now = datetime.now().isoformat(timespec="seconds")
        created_at = current.get("created_at") or now
        status = "Configurado" if host.strip() and database_name.strip() and username.strip() else "Pendente"
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO database_connections(
                    id, name, engine, host, port, database_name, username,
                    password_encrypted, ssl_mode, notes, status, is_active_candidate,
                    updated_by_user_id, created_at, updated_at
                )
                VALUES(1,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    engine=excluded.engine,
                    host=excluded.host,
                    port=excluded.port,
                    database_name=excluded.database_name,
                    username=excluded.username,
                    password_encrypted=excluded.password_encrypted,
                    ssl_mode=excluded.ssl_mode,
                    notes=excluded.notes,
                    status=excluded.status,
                    is_active_candidate=excluded.is_active_candidate,
                    updated_by_user_id=excluded.updated_by_user_id,
                    updated_at=excluded.updated_at
                """,
                (
                    name.strip(),
                    "postgresql" if engine != "postgresql" else engine,
                    host.strip(),
                    int(port or 5432),
                    database_name.strip(),
                    username.strip(),
                    encrypted_password,
                    ssl_mode if ssl_mode in {"prefer", "require", "disable"} else "prefer",
                    notes.strip(),
                    status,
                    "Sim" if status == "Configurado" else "Não",
                    updated_by_user_id,
                    created_at,
                    now,
                ),
            )
            connection.commit()

    def record_test_result(self, *, status: str, message: str) -> None:
        self._record_result(
            status_column="last_test_status",
            message_column="last_test_message",
            at_column="last_test_at",
            status=status,
            message=message,
        )

    def record_prepare_result(self, *, status: str, message: str) -> None:
        self._record_result(
            status_column="last_prepare_status",
            message_column="last_prepare_message",
            at_column="last_prepare_at",
            status=status,
            message=message,
        )

    def _record_result(
        self,
        *,
        status_column: str,
        message_column: str,
        at_column: str,
        status: str,
        message: str,
    ) -> None:
        self.init_schema()
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            connection.execute(
                f"""
                INSERT INTO database_connections(id, engine, {status_column}, {message_column}, {at_column}, updated_at)
                VALUES(1, 'postgresql', ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    {status_column}=excluded.{status_column},
                    {message_column}=excluded.{message_column},
                    {at_column}=excluded.{at_column},
                    updated_at=excluded.updated_at
                """,
                (status, message, now, now),
            )
            connection.commit()

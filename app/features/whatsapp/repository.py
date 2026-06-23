import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_DEPARTMENTS = ("Comercial", "Financeiro", "Pedidos", "Suporte")


class WhatsAppSettingsRepository:
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
                CREATE TABLE IF NOT EXISTS whatsapp_settings (
                    id INTEGER PRIMARY KEY CHECK (id=1),
                    enabled TEXT DEFAULT 'Não',
                    api_version TEXT DEFAULT 'v23.0',
                    phone_number_id TEXT,
                    whatsapp_business_account_id TEXT,
                    verify_token_hash TEXT,
                    access_token_encrypted TEXT,
                    app_secret_encrypted TEXT,
                    public_webhook_url TEXT,
                    setup_status TEXT DEFAULT 'Não configurado',
                    last_test_status TEXT,
                    last_test_message TEXT,
                    last_test_at TEXT,
                    updated_by_user_id INTEGER,
                    updated_at TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS whatsapp_departments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    description TEXT,
                    is_active TEXT DEFAULT 'Sim',
                    default_user_id INTEGER,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            now = datetime.now().isoformat(timespec="seconds")
            for name in DEFAULT_DEPARTMENTS:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO whatsapp_departments(name,description,is_active,created_at,updated_at)
                    VALUES(?,?,?,?,?)
                    """,
                    (name, f"Atendimento {name}", "Sim", now, now),
                )
            connection.commit()

    def get_settings(self) -> dict[str, Any]:
        self.init_schema()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM whatsapp_settings WHERE id=1",
            ).fetchone()
        if not row:
            return {
                "id": 1,
                "enabled": "Não",
                "api_version": "v23.0",
                "phone_number_id": "",
                "whatsapp_business_account_id": "",
                "verify_token_hash": "",
                "access_token_encrypted": "",
                "app_secret_encrypted": "",
                "public_webhook_url": "",
                "setup_status": "Não configurado",
                "last_test_status": "",
                "last_test_message": "",
                "last_test_at": "",
                "updated_by_user_id": None,
                "updated_at": "",
            }
        return dict(row)

    def save_settings(
        self,
        *,
        api_version: str,
        phone_number_id: str,
        whatsapp_business_account_id: str,
        public_webhook_url: str,
        access_token_encrypted: str | None,
        app_secret_encrypted: str | None,
        verify_token_hash: str | None,
        updated_by_user_id: int,
    ) -> None:
        current = self.get_settings()
        access_secret = access_token_encrypted or current.get("access_token_encrypted") or ""
        app_secret = app_secret_encrypted or current.get("app_secret_encrypted") or ""
        verify_hash = verify_token_hash or current.get("verify_token_hash") or ""
        status = "Configurado" if all(
            [
                phone_number_id.strip(),
                whatsapp_business_account_id.strip(),
                access_secret,
                app_secret,
                verify_hash,
            ],
        ) else "Credenciais pendentes"
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO whatsapp_settings(
                    id, enabled, api_version, phone_number_id,
                    whatsapp_business_account_id, verify_token_hash,
                    access_token_encrypted, app_secret_encrypted, public_webhook_url,
                    setup_status, updated_by_user_id, updated_at
                )
                VALUES(1,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    api_version=excluded.api_version,
                    phone_number_id=excluded.phone_number_id,
                    whatsapp_business_account_id=excluded.whatsapp_business_account_id,
                    verify_token_hash=excluded.verify_token_hash,
                    access_token_encrypted=excluded.access_token_encrypted,
                    app_secret_encrypted=excluded.app_secret_encrypted,
                    public_webhook_url=excluded.public_webhook_url,
                    setup_status=excluded.setup_status,
                    updated_by_user_id=excluded.updated_by_user_id,
                    updated_at=excluded.updated_at
                """,
                (
                    current.get("enabled") or "Não",
                    api_version.strip() or "v23.0",
                    phone_number_id.strip(),
                    whatsapp_business_account_id.strip(),
                    verify_hash,
                    access_secret,
                    app_secret,
                    public_webhook_url.strip(),
                    status,
                    updated_by_user_id,
                    now,
                ),
            )
            connection.commit()

    def set_enabled(self, enabled: bool, updated_by_user_id: int) -> None:
        self.init_schema()
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO whatsapp_settings(id, enabled, api_version, setup_status, updated_by_user_id, updated_at)
                VALUES(1,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    enabled=excluded.enabled,
                    updated_by_user_id=excluded.updated_by_user_id,
                    updated_at=excluded.updated_at
                """,
                ("Sim" if enabled else "Não", "v23.0", "Não configurado", updated_by_user_id, now),
            )
            connection.commit()

    def departments(self) -> list[dict[str, Any]]:
        self.init_schema()
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM whatsapp_departments ORDER BY id",
            ).fetchall()
        return [dict(row) for row in rows]

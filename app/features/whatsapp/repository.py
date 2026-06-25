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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS whatsapp_contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_e164 TEXT UNIQUE,
                    display_name TEXT,
                    profile_name TEXT,
                    origin TEXT,
                    client_id INTEGER,
                    first_seen_at TEXT,
                    last_seen_at TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS whatsapp_conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contact_id INTEGER UNIQUE,
                    chat_room_id INTEGER,
                    department_id INTEGER,
                    assigned_user_id INTEGER,
                    status TEXT DEFAULT 'triage',
                    last_message_at TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS whatsapp_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER,
                    provider_message_id TEXT UNIQUE,
                    direction TEXT,
                    sender_label TEXT,
                    content TEXT,
                    message_type TEXT,
                    media_path TEXT,
                    raw_payload_json TEXT,
                    status TEXT,
                    created_at TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS whatsapp_triage_states (
                    contact_id INTEGER PRIMARY KEY,
                    state TEXT,
                    context_json TEXT,
                    updated_at TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS whatsapp_embedded_signup_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_by_user_id INTEGER,
                    state_token_hash TEXT UNIQUE,
                    status TEXT,
                    provider_payload_json TEXT,
                    created_at TEXT,
                    completed_at TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS whatsapp_automation_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    trigger_type TEXT,
                    trigger_value TEXT,
                    response_type TEXT,
                    response_text TEXT,
                    target_department_id INTEGER,
                    is_active TEXT DEFAULT 'Sim',
                    created_by_user_id INTEGER,
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

    def record_test_status(
        self,
        *,
        status: str,
        message: str,
        updated_by_user_id: int,
    ) -> None:
        self.init_schema()
        now = datetime.now().isoformat(timespec="seconds")
        safe_message = message[:500]
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO whatsapp_settings(
                    id, enabled, api_version, setup_status,
                    last_test_status, last_test_message, last_test_at,
                    updated_by_user_id, updated_at
                )
                VALUES(1,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    setup_status=CASE WHEN ?='success' THEN 'Testado' ELSE whatsapp_settings.setup_status END,
                    last_test_status=excluded.last_test_status,
                    last_test_message=excluded.last_test_message,
                    last_test_at=excluded.last_test_at,
                    updated_by_user_id=excluded.updated_by_user_id,
                    updated_at=excluded.updated_at
                """,
                (
                    "Não",
                    "v23.0",
                    "Não configurado",
                    status,
                    safe_message,
                    now,
                    updated_by_user_id,
                    now,
                    status,
                ),
            )
            connection.commit()

    def departments(self) -> list[dict[str, Any]]:
        self.init_schema()
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM whatsapp_departments ORDER BY id",
            ).fetchall()
        return [dict(row) for row in rows]

    def active_users(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT id, username, role FROM users WHERE active='Sim' ORDER BY username",
            ).fetchall()
        return [dict(row) for row in rows]

    def save_departments(self, form_data: dict[str, str], updated_by_user_id: int) -> None:
        self.init_schema()
        now = datetime.now().isoformat(timespec="seconds")
        departments = self.departments()
        with self.connect() as connection:
            for department in departments:
                department_id = int(department["id"])
                active = "Sim" if form_data.get(f"department_{department_id}_active") else "Não"
                raw_user_id = form_data.get(f"department_{department_id}_default_user_id") or ""
                default_user_id = int(raw_user_id) if raw_user_id.isdigit() else None
                connection.execute(
                    """
                    UPDATE whatsapp_departments
                    SET is_active=?, default_user_id=?, updated_at=?
                    WHERE id=?
                    """,
                    (active, default_user_id, now, department_id),
                )
            connection.commit()

    def create_embedded_signup_session(
        self,
        *,
        started_by_user_id: int,
        state_token_hash: str,
    ) -> int:
        self.init_schema()
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO whatsapp_embedded_signup_sessions(
                    started_by_user_id,state_token_hash,status,provider_payload_json,created_at
                )
                VALUES(?,?,?,?,?)
                """,
                (started_by_user_id, state_token_hash, "pending", "{}", now),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def find_embedded_signup_session(
        self,
        state_token_hash: str,
    ) -> dict[str, Any] | None:
        self.init_schema()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM whatsapp_embedded_signup_sessions WHERE state_token_hash=?",
                (state_token_hash,),
            ).fetchone()
        return dict(row) if row else None

    def complete_embedded_signup_session(
        self,
        *,
        state_token_hash: str,
        provider_payload_json: str,
    ) -> bool:
        self.init_schema()
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE whatsapp_embedded_signup_sessions
                SET status='completed', provider_payload_json=?, completed_at=?
                WHERE state_token_hash=? AND status='pending'
                """,
                (provider_payload_json, now, state_token_hash),
            )
            connection.commit()
        return cursor.rowcount > 0

    def automation_rules(self) -> list[dict[str, Any]]:
        self.init_schema()
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT rule.*, department.name AS target_department_name
                FROM whatsapp_automation_rules rule
                LEFT JOIN whatsapp_departments department
                    ON department.id = rule.target_department_id
                ORDER BY rule.id DESC
                """,
            ).fetchall()
        return [dict(row) for row in rows]

    def create_automation_rule(
        self,
        *,
        name: str,
        trigger_type: str,
        trigger_value: str,
        response_type: str,
        response_text: str,
        target_department_id: int | None,
        is_active: bool,
        created_by_user_id: int,
    ) -> int:
        self.init_schema()
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO whatsapp_automation_rules(
                    name, trigger_type, trigger_value, response_type,
                    response_text, target_department_id, is_active,
                    created_by_user_id, created_at, updated_at
                )
                VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    name.strip(),
                    trigger_type.strip() or "keyword",
                    trigger_value.strip(),
                    response_type.strip() or "human_handoff",
                    response_text.strip(),
                    target_department_id,
                    "Sim" if is_active else "Não",
                    created_by_user_id,
                    now,
                    now,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def find_message(self, provider_message_id: str) -> dict[str, Any] | None:
        self.init_schema()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM whatsapp_messages WHERE provider_message_id=?",
                (provider_message_id,),
            ).fetchone()
        return dict(row) if row else None

    def upsert_contact(self, phone: str, profile_name: str) -> dict[str, Any]:
        self.init_schema()
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            existing = connection.execute(
                "SELECT * FROM whatsapp_contacts WHERE phone_e164=?",
                (phone,),
            ).fetchone()
            if existing:
                connection.execute(
                    """
                    UPDATE whatsapp_contacts
                    SET profile_name=?, display_name=COALESCE(NULLIF(display_name,''), ?),
                        last_seen_at=?, updated_at=?
                    WHERE id=?
                    """,
                    (profile_name, profile_name, now, now, existing["id"]),
                )
                contact_id = existing["id"]
            else:
                contact_id = connection.execute(
                    """
                    INSERT INTO whatsapp_contacts(
                        phone_e164, display_name, profile_name,
                        first_seen_at, last_seen_at, created_at, updated_at
                    )
                    VALUES(?,?,?,?,?,?,?)
                    """,
                    (phone, profile_name, profile_name, now, now, now, now),
                ).lastrowid
            connection.commit()
            row = connection.execute(
                "SELECT * FROM whatsapp_contacts WHERE id=?",
                (contact_id,),
            ).fetchone()
        return dict(row)

    def ensure_conversation(self, contact: dict[str, Any]) -> dict[str, Any]:
        self.init_schema()
        now = datetime.now().isoformat(timespec="seconds")
        label = contact.get("display_name") or contact.get("profile_name") or contact["phone_e164"]
        with self.connect() as connection:
            existing = connection.execute(
                "SELECT * FROM whatsapp_conversations WHERE contact_id=?",
                (contact["id"],),
            ).fetchone()
            if existing:
                conversation_id = existing["id"]
                chat_room_id = existing["chat_room_id"]
            else:
                chat_room_id = connection.execute(
                    "INSERT INTO chat_rooms(name,created_at,room_type) VALUES(?,?,?)",
                    (f"WhatsApp · {label}", now, "whatsapp"),
                ).lastrowid
                conversation_id = connection.execute(
                    """
                    INSERT INTO whatsapp_conversations(contact_id,chat_room_id,status,last_message_at,created_at,updated_at)
                    VALUES(?,?,?,?,?,?)
                    """,
                    (contact["id"], chat_room_id, "triage", now, now, now),
                ).lastrowid
            connection.execute(
                "UPDATE whatsapp_conversations SET last_message_at=?, updated_at=? WHERE id=?",
                (now, now, conversation_id),
            )
            connection.commit()
            row = connection.execute(
                "SELECT * FROM whatsapp_conversations WHERE id=?",
                (conversation_id,),
            ).fetchone()
        return dict(row)

    def insert_inbound_message(
        self,
        *,
        conversation_id: int,
        provider_message_id: str,
        sender_label: str,
        content: str,
        message_type: str,
        raw_payload_json: str,
    ) -> bool:
        self.init_schema()
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO whatsapp_messages(
                        conversation_id, provider_message_id, direction, sender_label,
                        content, message_type, raw_payload_json, status, created_at
                    )
                    VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        conversation_id,
                        provider_message_id,
                        "inbound",
                        sender_label,
                        content,
                        message_type,
                        raw_payload_json,
                        "received",
                        now,
                    ),
                )
            except sqlite3.IntegrityError:
                return False
            connection.commit()
        return True

    def mirror_to_chat(self, chat_room_id: int, sender_label: str, content: str) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO chat_messages(room_id,user_id,content,attachment_path,created_at) VALUES(?,?,?,?,?)",
                (chat_room_id, None, f"WhatsApp · {sender_label}: {content}", None, now),
            )
            connection.commit()

    def get_triage_state(self, contact_id: int) -> str | None:
        self.init_schema()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT state FROM whatsapp_triage_states WHERE contact_id=?",
                (contact_id,),
            ).fetchone()
        return row["state"] if row else None

    def set_triage_state(self, contact_id: int, state: str) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO whatsapp_triage_states(contact_id,state,context_json,updated_at)
                VALUES(?,?,?,?)
                ON CONFLICT(contact_id) DO UPDATE SET
                    state=excluded.state,
                    updated_at=excluded.updated_at
                """,
                (contact_id, state, "{}", now),
            )
            connection.commit()

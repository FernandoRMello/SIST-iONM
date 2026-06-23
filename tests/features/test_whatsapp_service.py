import sqlite3
from pathlib import Path

from app.features.whatsapp.repository import WhatsAppSettingsRepository
from app.features.whatsapp.service import (
    handle_inbound_message,
    normalize_inbound_payload,
)


def _prepare_database(path: Path) -> WhatsAppSettingsRepository:
    repository = WhatsAppSettingsRepository(path)
    repository.init_schema()
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS chat_rooms (id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,created_at TEXT,room_type TEXT,user1_id INTEGER,user2_id INTEGER)",
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS chat_messages (id INTEGER PRIMARY KEY AUTOINCREMENT,room_id INTEGER,user_id INTEGER,content TEXT,attachment_path TEXT,created_at TEXT)",
        )
        connection.commit()
    return repository


def test_normalize_inbound_payload_extracts_text_message() -> None:
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "contacts": [
                                {
                                    "wa_id": "5511999999999",
                                    "profile": {"name": "Cliente Teste"},
                                },
                            ],
                            "messages": [
                                {
                                    "id": "wamid.TEST1",
                                    "from": "5511999999999",
                                    "type": "text",
                                    "text": {"body": "Olá"},
                                },
                            ],
                        },
                    },
                ],
            },
        ],
    }

    messages = normalize_inbound_payload(payload)

    assert len(messages) == 1
    assert messages[0].provider_message_id == "wamid.TEST1"
    assert messages[0].from_phone == "5511999999999"
    assert messages[0].profile_name == "Cliente Teste"
    assert messages[0].content == "Olá"


def test_handle_inbound_message_creates_contact_conversation_and_chat(tmp_path: Path) -> None:
    repository = _prepare_database(tmp_path / "whatsapp.db")
    message = normalize_inbound_payload(
        {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "contacts": [{"wa_id": "5511888888888", "profile": {"name": "Ana"}}],
                                "messages": [
                                    {
                                        "id": "wamid.ANA1",
                                        "from": "5511888888888",
                                        "type": "text",
                                        "text": {"body": "financeiro"},
                                    },
                                ],
                            },
                        },
                    ],
                },
            ],
        },
    )[0]

    result = handle_inbound_message(repository, message)
    duplicate = handle_inbound_message(repository, message)

    assert result.created is True
    assert result.auto_reply.startswith("Olá! Sou o assistente")
    assert duplicate.created is False
    with sqlite3.connect(repository.database_path) as connection:
        contact_count = connection.execute("SELECT COUNT(*) FROM whatsapp_contacts").fetchone()[0]
        conversation = connection.execute("SELECT chat_room_id FROM whatsapp_conversations").fetchone()
        chat_message = connection.execute("SELECT content FROM chat_messages").fetchone()
    assert contact_count == 1
    assert conversation[0] is not None
    assert "financeiro" in chat_message[0]

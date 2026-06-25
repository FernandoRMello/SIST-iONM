import sqlite3
from pathlib import Path

from app.features.whatsapp.repository import WhatsAppSettingsRepository
from app.features.whatsapp.security import hash_state_token
from app.features.whatsapp.service import (
    handle_inbound_message,
    normalize_inbound_payload,
    resolve_automation_reply,
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


def test_embedded_signup_session_is_completed_by_state_hash(tmp_path: Path) -> None:
    repository = _prepare_database(tmp_path / "whatsapp.db")
    state_hash = hash_state_token("state-token-123")

    session_id = repository.create_embedded_signup_session(
        started_by_user_id=1,
        state_token_hash=state_hash,
    )
    completed = repository.complete_embedded_signup_session(
        state_token_hash=state_hash,
        provider_payload_json='{"phone_number_id":"123"}',
    )
    session = repository.find_embedded_signup_session(state_hash)

    assert session_id > 0
    assert completed is True
    assert session["status"] == "completed"
    assert "phone_number_id" in session["provider_payload_json"]


def test_finance_keyword_without_client_returns_safe_handoff(tmp_path: Path) -> None:
    repository = _prepare_database(tmp_path / "whatsapp.db")
    contact = repository.upsert_contact("5511999990000", "Cliente")
    repository.create_automation_rule(
        name="Financeiro",
        trigger_type="keyword",
        trigger_value="fatura,boleto",
        response_type="safe_finance_lookup",
        response_text="",
        target_department_id=None,
        is_active=True,
        created_by_user_id=1,
    )

    reply = resolve_automation_reply(repository, contact, "quero minha fatura")

    assert "preciso confirmar seu cadastro" in reply


def test_human_keyword_routes_to_attendant(tmp_path: Path) -> None:
    repository = _prepare_database(tmp_path / "whatsapp.db")
    contact = repository.upsert_contact("5511999990001", "Cliente")

    reply = resolve_automation_reply(repository, contact, "falar com atendente")

    assert "encaminhar para um atendente" in reply


def test_linked_client_receivables_are_returned_without_leaking_other_clients(
    tmp_path: Path,
) -> None:
    repository = _prepare_database(tmp_path / "whatsapp.db")
    contact = repository.upsert_contact("5511999990002", "Cliente")
    with sqlite3.connect(repository.database_path) as connection:
        connection.execute(
            "CREATE TABLE receivables (id INTEGER PRIMARY KEY, client_id INTEGER, description TEXT, amount REAL, due_date TEXT, status TEXT)",
        )
        connection.execute(
            "UPDATE whatsapp_contacts SET client_id=10 WHERE id=?",
            (contact["id"],),
        )
        connection.execute(
            "INSERT INTO receivables(client_id,description,amount,due_date,status) VALUES(?,?,?,?,?)",
            (10, "FAT-QA-0001", 1234.56, "2026-07-10", "Aberto"),
        )
        connection.execute(
            "INSERT INTO receivables(client_id,description,amount,due_date,status) VALUES(?,?,?,?,?)",
            (20, "FAT-OUTRO-CLIENTE", 9999.99, "2026-07-11", "Aberto"),
        )
        connection.commit()
    contact = repository.upsert_contact("5511999990002", "Cliente")
    repository.create_automation_rule(
        name="Financeiro",
        trigger_type="keyword",
        trigger_value="fatura",
        response_type="safe_finance_lookup",
        response_text="",
        target_department_id=None,
        is_active=True,
        created_by_user_id=1,
    )

    reply = resolve_automation_reply(repository, contact, "minha fatura")

    assert "FAT-QA-0001" in reply
    assert "R$ 1.234,56" in reply
    assert "FAT-OUTRO-CLIENTE" not in reply


def test_linked_client_orders_are_returned_without_leaking_other_clients(
    tmp_path: Path,
) -> None:
    repository = _prepare_database(tmp_path / "whatsapp.db")
    contact = repository.upsert_contact("5511999990003", "Cliente")
    with sqlite3.connect(repository.database_path) as connection:
        connection.execute(
            "CREATE TABLE orders (id INTEGER PRIMARY KEY, client_id INTEGER, order_number TEXT, total_amount REAL, status TEXT, created_at TEXT)",
        )
        connection.execute(
            "UPDATE whatsapp_contacts SET client_id=10 WHERE id=?",
            (contact["id"],),
        )
        connection.execute(
            "INSERT INTO orders(client_id,order_number,total_amount,status,created_at) VALUES(?,?,?,?,?)",
            (10, "PED-QA-0001", 456.78, "Aberto", "2026-07-12"),
        )
        connection.execute(
            "INSERT INTO orders(client_id,order_number,total_amount,status,created_at) VALUES(?,?,?,?,?)",
            (20, "PED-OUTRO-CLIENTE", 999.99, "Aberto", "2026-07-13"),
        )
        connection.commit()
    contact = repository.upsert_contact("5511999990003", "Cliente")
    repository.create_automation_rule(
        name="Pedidos",
        trigger_type="keyword",
        trigger_value="pedido",
        response_type="safe_order_lookup",
        response_text="",
        target_department_id=None,
        is_active=True,
        created_by_user_id=1,
    )

    reply = resolve_automation_reply(repository, contact, "meu pedido")

    assert "PED-QA-0001" in reply
    assert "R$ 456,78" in reply
    assert "PED-OUTRO-CLIENTE" not in reply

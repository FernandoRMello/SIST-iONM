import re
import sqlite3

from fastapi.testclient import TestClient

from app.main import pagination_values
from tests.conftest import LegacyTestState


def test_pagination_values_normalizes_limits() -> None:
    assert pagination_values(total=250, page=-5, page_size=0) == {
        "page": 1,
        "page_size": 25,
        "total": 250,
        "pages": 10,
    }
    assert pagination_values(total=250, page=999, page_size=500) == {
        "page": 3,
        "page_size": 100,
        "total": 250,
        "pages": 3,
    }


def test_versioned_assets_are_cached_but_html_is_private(legacy_client) -> None:
    asset = legacy_client.get("/assets/css/tokens.css?v=20260618")
    login = legacy_client.get("/login")

    assert asset.status_code == 200
    assert asset.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert login.headers["cache-control"] == "no-store"


def table_row_count(html: str, table_id: str) -> int:
    table = re.search(
        rf'<table[^>]*id="{table_id}"[^>]*>.*?<tbody>(?P<body>.*?)</tbody>',
        html,
        re.DOTALL,
    )
    assert table is not None
    return len(re.findall(r"<tr(?:\s|>)", table.group("body")))


def test_large_lists_render_only_the_requested_page(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        connection.execute(
            "INSERT INTO clients(name,email) VALUES(?,?)",
            ("Cliente Paginação", "pagination@example.invalid"),
        )
        connection.execute(
            "INSERT INTO receivables(description,amount,status) VALUES(?,?,?)",
            ("Recebível paginação", 123, "Aberto"),
        )
        room_id = connection.execute(
            "SELECT id FROM chat_rooms ORDER BY id LIMIT 1"
        ).fetchone()[0]
        user_id = connection.execute(
            "SELECT id FROM users ORDER BY id LIMIT 1"
        ).fetchone()[0]
        connection.executemany(
            "INSERT INTO chat_messages(room_id,user_id,content,created_at) VALUES(?,?,?,?)",
            [
                (room_id, user_id, "Mensagem paginação 1", "2026-06-18T12:00:00"),
                (room_id, user_id, "Mensagem paginação 2", "2026-06-18T12:01:00"),
            ],
        )
        connection.execute(
            "INSERT INTO sellers(name,active) VALUES(?,?)",
            ("Vendedor Paginação", "Sim"),
        )
        connection.commit()

    responses = {
        "crud-records": admin_client.get("/cadastros/clients?page_size=1"),
        "finance-table": admin_client.get("/finance?segment=receivables&page_size=1"),
        "seller-report-table": admin_client.get("/reports/sellers?page_size=1"),
    }
    for table_id, response in responses.items():
        assert response.status_code == 200
        assert table_row_count(response.text, table_id) == 1
        assert "Página 1 de" in response.text

    chat = admin_client.get(f"/chat?room_id={room_id}&page_size=1")
    assert chat.status_code == 200
    messages = re.search(
        r'id="fullChatMessages"[^>]*>(?P<body>.*?)</div>',
        chat.text,
        re.DOTALL,
    )
    assert messages is not None
    assert len(re.findall(r'<article class="ui-message', messages.group("body"))) == 1
    assert "Página 1 de" in chat.text

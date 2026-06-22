import sqlite3

from fastapi.testclient import TestClient

from tests.conftest import LegacyTestState


def general_room_id(state: LegacyTestState) -> int:
    with sqlite3.connect(state.database_path) as connection:
        return int(
            connection.execute(
                "SELECT id FROM chat_rooms WHERE room_type='general' ORDER BY id LIMIT 1"
            ).fetchone()[0]
        )


def test_marking_room_read_persists_last_message(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    room_id = general_room_id(legacy_test_state)

    response = admin_client.post(f"/chat/read/{room_id}")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "room_id": room_id, "unread": 0}
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        row = connection.execute(
            "SELECT last_read_message_id FROM chat_read_state WHERE room_id=?",
            (room_id,),
        ).fetchone()
    assert row is not None


def test_chat_context_restores_unread_counts(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    room_id = general_room_id(legacy_test_state)
    admin_client.post(f"/chat/read/{room_id}")
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        sender_id = legacy_test_state.ids["settings_user_id"]
        connection.execute(
            "INSERT INTO chat_messages(room_id,user_id,content,attachment_path,created_at) VALUES(?,?,?,?,?)",
            (room_id, sender_id, "Nova não lida", "", "2026-06-22T14:00:00"),
        )

    response = admin_client.get("/chat/context")

    assert response.status_code == 200
    assert response.json()["unread"][str(room_id)] == 1


def test_mark_read_rejects_inaccessible_room(
    authenticated_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        admin_id = connection.execute(
            "SELECT id FROM users WHERE username=?",
            (legacy_test_state.admin_username,),
        ).fetchone()[0]
        other_id = connection.execute(
            "INSERT INTO users(username,password_hash,role,active) VALUES(?,?,?,?)",
            ("outside.user", "unused", "vendedor", "Sim"),
        ).lastrowid
        room_id = connection.execute(
            "INSERT INTO chat_rooms(name,created_at,room_type,user1_id,user2_id) VALUES(?,?,?,?,?)",
            ("Privada", "2026-06-22T14:00:00", "private", admin_id, other_id),
        ).lastrowid

    response = authenticated_client.post(f"/chat/read/{room_id}")

    assert response.status_code == 403


def test_message_sent_by_websocket_reaches_recipient_notification_socket(
    legacy_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    room_id = general_room_id(legacy_test_state)
    admin_login = legacy_client.post(
        "/login",
        data={
            "username": legacy_test_state.admin_username,
            "password": legacy_test_state.admin_password,
        },
        follow_redirects=False,
    )
    assert admin_login.status_code == 303

    with legacy_client.websocket_connect("/ws/notify") as notification_socket:
        seller_login = legacy_client.post(
            "/login",
            data={
                "username": legacy_test_state.seller_username,
                "password": legacy_test_state.seller_password,
            },
            follow_redirects=False,
        )
        assert seller_login.status_code == 303
        with legacy_client.websocket_connect(f"/ws/chat/{room_id}") as sender_socket:
            sender_socket.send_json({"content": "Notificação em tempo real"})
            payload = notification_socket.receive_json()

    assert payload["type"] == "chat_message"
    assert payload["room_id"] == room_id
    assert payload["message"]["content"] == "Notificação em tempo real"
    assert payload["message"]["user_id"] == legacy_test_state.ids["settings_user_id"]

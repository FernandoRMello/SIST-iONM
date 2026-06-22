import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as legacy
from tests.conftest import LegacyTestState


class RecordingChatManager:
    def __init__(self) -> None:
        self.deliveries: list[tuple[int, dict]] = []

    async def broadcast(self, room_id: int, payload: dict) -> None:
        self.deliveries.append((room_id, payload))


class RecordingNotificationManager:
    def __init__(self) -> None:
        self.deliveries: list[tuple[int, dict]] = []

    async def notify(self, user_id: int, payload: dict) -> None:
        self.deliveries.append((user_id, payload))


def general_room_id(state: LegacyTestState) -> int:
    with sqlite3.connect(state.database_path) as connection:
        return int(
            connection.execute(
                "SELECT id FROM chat_rooms WHERE room_type='general' ORDER BY id LIMIT 1"
            ).fetchone()[0]
        )


def test_chat_attachment_is_saved_broadcast_and_notified(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
    monkeypatch,
    tmp_path: Path,
) -> None:
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    chat_manager = RecordingChatManager()
    notification_manager = RecordingNotificationManager()
    monkeypatch.setattr(legacy, "UPLOAD_DIR", uploads)
    monkeypatch.setattr(legacy, "chat_manager", chat_manager)
    monkeypatch.setattr(legacy, "notify_manager", notification_manager)
    room_id = general_room_id(legacy_test_state)

    response = admin_client.post(
        "/chat/send",
        data={"room_id": str(room_id), "content": "Segue o documento"},
        files={"attachment": ("proposta.pdf", b"%PDF-1.4 test", "application/pdf")},
        headers={"accept": "application/json"},
    )

    assert response.status_code == 200
    payload = response.json()["message"]
    assert payload["content"] == "Segue o documento"
    assert payload["attachment_path"].startswith("uploads/chat_")
    assert "proposta" not in payload["attachment_path"]
    assert len(list(uploads.iterdir())) == 1
    assert chat_manager.deliveries == [(room_id, payload)]
    assert any(
        delivery[1]["message"] == payload
        for delivery in notification_manager.deliveries
    )


def test_chat_rejects_unsafe_attachment_extension(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
    monkeypatch,
    tmp_path: Path,
) -> None:
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    monkeypatch.setattr(legacy, "UPLOAD_DIR", uploads)

    response = admin_client.post(
        "/chat/send",
        data={"room_id": str(general_room_id(legacy_test_state)), "content": ""},
        files={"attachment": ("programa.exe", b"unsafe", "application/octet-stream")},
        headers={"accept": "application/json"},
    )

    assert response.status_code == 400
    assert "formato" in response.json()["error"].lower()
    assert list(uploads.iterdir()) == []


def test_chat_rejects_attachment_above_the_size_limit(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
    monkeypatch,
    tmp_path: Path,
) -> None:
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    monkeypatch.setattr(legacy, "UPLOAD_DIR", uploads)
    monkeypatch.setattr(legacy, "MAX_CHAT_ATTACHMENT_BYTES", 8)

    response = admin_client.post(
        "/chat/send",
        data={"room_id": str(general_room_id(legacy_test_state)), "content": ""},
        files={"attachment": ("grande.pdf", b"123456789", "application/pdf")},
        headers={"accept": "application/json"},
    )

    assert response.status_code == 400
    assert "limite" in response.json()["error"].lower()
    assert list(uploads.iterdir()) == []

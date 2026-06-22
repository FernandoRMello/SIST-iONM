import sqlite3
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

import app.main as legacy
from tests.conftest import LegacyTestState


def png_bytes() -> bytes:
    image = Image.new("RGB", (800, 400), (14, 114, 116))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def profile_avatar_path(state: LegacyTestState) -> str:
    with sqlite3.connect(state.database_path) as connection:
        return str(
            connection.execute(
                """
                SELECT up.avatar_path
                FROM user_profiles up
                JOIN users u ON u.id=up.user_id
                WHERE u.username=?
                """,
                (state.admin_username,),
            ).fetchone()[0]
            or ""
        )


def test_profile_upload_saves_normalized_avatar(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(legacy, "UPLOAD_DIR", tmp_path)

    response = admin_client.post(
        "/profile/avatar",
        files={"avatar": ("portrait.png", png_bytes(), "image/png")},
        follow_redirects=False,
    )

    assert response.status_code == 303
    stored = profile_avatar_path(legacy_test_state)
    saved = tmp_path / Path(stored).name
    assert saved.exists()
    image = Image.open(saved)
    assert image.size == (512, 512)
    assert image.format == "JPEG"


def test_invalid_profile_upload_preserves_current_avatar(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(legacy, "UPLOAD_DIR", tmp_path)
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        connection.execute(
            """
            UPDATE user_profiles SET avatar_path='uploads/current.jpg'
            WHERE user_id=(SELECT id FROM users WHERE username=?)
            """,
            (legacy_test_state.admin_username,),
        )

    response = admin_client.post(
        "/profile/avatar",
        files={"avatar": ("broken.jpg", b"broken", "image/jpeg")},
    )

    assert response.status_code == 400
    assert profile_avatar_path(legacy_test_state) == "uploads/current.jpg"

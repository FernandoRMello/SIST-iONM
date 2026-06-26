import sqlite3

from fastapi.testclient import TestClient

from app.features.database_admin.service import OperationResult
from tests.conftest import LegacyTestState


def test_settings_page_renders_database_area_for_admin(admin_client: TestClient) -> None:
    response = admin_client.get("/settings")

    assert response.status_code == 200
    assert "Banco de dados" in response.text
    assert "PostgreSQL" in response.text
    assert 'action="/settings/database/save"' in response.text
    assert 'action="/settings/database/test"' in response.text
    assert 'action="/settings/database/prepare"' in response.text
    assert "reinício do servidor" in response.text


def test_non_admin_cannot_change_database_settings(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.post(
        "/settings/database/save",
        data={
            "name": "Banco bloqueado",
            "host": "127.0.0.1",
            "port": "5432",
            "database_name": "sist_ionm",
            "username": "sist_ionm",
            "password": "secret",
            "ssl_mode": "prefer",
            "notes": "",
        },
    )

    assert response.status_code == 403


def test_database_password_is_not_rendered_after_save(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    secret = "PG-SECRET-MUST-NOT-LEAK"
    response = admin_client.post(
        "/settings/database/save",
        data={
            "name": "PostgreSQL Local",
            "host": "127.0.0.1",
            "port": "5432",
            "database_name": "sist_ionm",
            "username": "sist_ionm",
            "password": secret,
            "ssl_mode": "prefer",
            "notes": "Servidor Ubuntu",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    page = admin_client.get("/settings")
    assert secret not in page.text
    assert "Configurada" in page.text
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        encrypted = connection.execute(
            "SELECT password_encrypted FROM database_connections WHERE id=1",
        ).fetchone()[0]
    assert encrypted
    assert encrypted != secret


def test_database_test_and_prepare_routes_record_statuses(
    admin_client: TestClient,
    monkeypatch,
    legacy_test_state: LegacyTestState,
) -> None:
    admin_client.post(
        "/settings/database/save",
        data={
            "name": "PostgreSQL Local",
            "host": "127.0.0.1",
            "port": "5432",
            "database_name": "sist_ionm",
            "username": "sist_ionm",
            "password": "secret",
            "ssl_mode": "prefer",
            "notes": "",
        },
    )

    def fake_test(self, config, password):
        assert password == "secret"
        return OperationResult("success", "Conexão realizada com sucesso.")

    def fake_prepare(self, config, password):
        assert password == "secret"
        return OperationResult("success", "Ambiente PostgreSQL preparado para migração/cutover.")

    monkeypatch.setattr(
        "app.features.database_admin.routes.DatabaseAdminService.test_connection",
        fake_test,
    )
    monkeypatch.setattr(
        "app.features.database_admin.routes.DatabaseAdminService.prepare_environment",
        fake_prepare,
    )

    tested = admin_client.post("/settings/database/test", follow_redirects=False)
    prepared = admin_client.post("/settings/database/prepare", follow_redirects=False)

    assert tested.status_code == 303
    assert prepared.status_code == 303
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute("SELECT * FROM database_connections WHERE id=1").fetchone()
    assert row["last_test_status"] == "success"
    assert row["last_test_message"] == "Conexão realizada com sucesso."
    assert row["last_prepare_status"] == "success"
    assert row["last_prepare_message"] == "Ambiente PostgreSQL preparado para migração/cutover."

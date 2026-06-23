import sqlite3

from fastapi.testclient import TestClient

from tests.conftest import LegacyTestState


def test_whatsapp_wizard_is_admin_only(
    authenticated_client: TestClient,
    admin_client: TestClient,
) -> None:
    denied = authenticated_client.get("/admin/integrations/whatsapp")
    allowed = admin_client.get("/admin/integrations/whatsapp")

    assert denied.status_code == 403
    assert allowed.status_code == 200
    assert "WhatsApp Business" in allowed.text
    assert "API oficial da Meta" in allowed.text


def test_admin_menu_links_to_whatsapp_wizard(admin_client: TestClient) -> None:
    response = admin_client.get("/")

    assert response.status_code == 200
    assert 'href="/admin/integrations/whatsapp"' in response.text
    assert "WhatsApp Business" in response.text


def test_whatsapp_wizard_saves_secrets_without_rendering_them(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    secret_token = "EAAB-SECRET-TOKEN-MUST-NOT-LEAK"
    app_secret = "APP-SECRET-MUST-NOT-LEAK"
    verify_token = "VERIFY-TOKEN-MUST-NOT-LEAK"

    response = admin_client.post(
        "/admin/integrations/whatsapp/save",
        data={
            "api_version": "v23.0",
            "phone_number_id": "123456789",
            "whatsapp_business_account_id": "987654321",
            "public_webhook_url": "https://example.com/integrations/whatsapp/webhook",
            "access_token": secret_token,
            "app_secret": app_secret,
            "verify_token": verify_token,
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    page = admin_client.get("/admin/integrations/whatsapp")
    assert page.status_code == 200
    assert secret_token not in page.text
    assert app_secret not in page.text
    assert verify_token not in page.text
    assert "Configurado" in page.text

    with sqlite3.connect(legacy_test_state.database_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute("SELECT * FROM whatsapp_settings WHERE id=1").fetchone()

    assert row["phone_number_id"] == "123456789"
    assert row["access_token_encrypted"] != secret_token
    assert row["app_secret_encrypted"] != app_secret
    assert row["verify_token_hash"] != verify_token


def test_non_admin_cannot_change_whatsapp_settings(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.post(
        "/admin/integrations/whatsapp/save",
        data={"phone_number_id": "123"},
        follow_redirects=False,
    )

    assert response.status_code == 403

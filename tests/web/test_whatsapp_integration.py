import sqlite3
import hashlib
import hmac

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


def test_admin_can_configure_whatsapp_departments(
    admin_client: TestClient,
    authenticated_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    forbidden = authenticated_client.post(
        "/admin/integrations/whatsapp/departments",
        data={"department_1_active": "Sim"},
        follow_redirects=False,
    )
    assert forbidden.status_code == 403

    response = admin_client.post(
        "/admin/integrations/whatsapp/departments",
        data={
            "department_1_active": "Sim",
            "department_1_default_user_id": str(legacy_test_state.ids["settings_user_id"]),
            "department_2_default_user_id": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        connection.row_factory = sqlite3.Row
        department = connection.execute(
            "SELECT default_user_id,is_active FROM whatsapp_departments WHERE id=1",
        ).fetchone()
    assert department["default_user_id"] == legacy_test_state.ids["settings_user_id"]
    assert department["is_active"] == "Sim"


def _save_valid_whatsapp_settings(admin_client: TestClient) -> None:
    response = admin_client.post(
        "/admin/integrations/whatsapp/save",
        data={
            "api_version": "v23.0",
            "phone_number_id": "123456789",
            "whatsapp_business_account_id": "987654321",
            "public_webhook_url": "https://example.com/integrations/whatsapp/webhook",
            "access_token": "EAAB-TEST",
            "app_secret": "APP-SECRET-WEBHOOK",
            "verify_token": "VERIFY-WEBHOOK",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_whatsapp_webhook_verification_uses_saved_verify_token(
    admin_client: TestClient,
) -> None:
    _save_valid_whatsapp_settings(admin_client)

    valid = admin_client.get(
        "/integrations/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "VERIFY-WEBHOOK",
            "hub.challenge": "challenge-123",
        },
    )
    invalid = admin_client.get(
        "/integrations/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong",
            "hub.challenge": "challenge-123",
        },
    )

    assert valid.status_code == 200
    assert valid.text == "challenge-123"
    assert invalid.status_code == 403


def test_whatsapp_webhook_rejects_invalid_post_signature(
    admin_client: TestClient,
) -> None:
    _save_valid_whatsapp_settings(admin_client)

    response = admin_client.post(
        "/integrations/whatsapp/webhook",
        content=b'{"entry":[]}',
        headers={"X-Hub-Signature-256": "sha256=invalid"},
    )

    assert response.status_code == 403


def test_whatsapp_webhook_persists_signed_message_and_deduplicates(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    _save_valid_whatsapp_settings(admin_client)
    body = (
        b'{"entry":[{"changes":[{"value":{"contacts":[{"wa_id":"5511999999999",'
        b'"profile":{"name":"Cliente Teste"}}],"messages":[{"id":"wamid.TEST1",'
        b'"from":"5511999999999","type":"text","text":{"body":"Ola"}}]}}]}]}'
    )
    digest = hmac.new(b"APP-SECRET-WEBHOOK", body, hashlib.sha256).hexdigest()
    headers = {"X-Hub-Signature-256": f"sha256={digest}"}

    first = admin_client.post(
        "/integrations/whatsapp/webhook",
        content=body,
        headers=headers,
    )
    second = admin_client.post(
        "/integrations/whatsapp/webhook",
        content=body,
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        message_count = connection.execute(
            "SELECT COUNT(*) FROM whatsapp_messages WHERE provider_message_id='wamid.TEST1'",
        ).fetchone()[0]
        chat_count = connection.execute(
            "SELECT COUNT(*) FROM chat_messages WHERE content LIKE '%Ola%'",
        ).fetchone()[0]
    assert message_count == 1
    assert chat_count == 1


def test_whatsapp_wizard_test_connection_uses_meta_client_without_leaking_secret(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
    monkeypatch,
) -> None:
    _save_valid_whatsapp_settings(admin_client)
    calls = []

    class FakeMetaClient:
        def send_text(self, *, api_version, phone_number_id, access_token, to_phone, message):
            calls.append(
                {
                    "api_version": api_version,
                    "phone_number_id": phone_number_id,
                    "access_token": access_token,
                    "to_phone": to_phone,
                    "message": message,
                },
            )
            return {"messages": [{"id": "wamid.TEST-SEND"}]}

    monkeypatch.setattr(
        "app.features.whatsapp.routes.MetaWhatsAppClient",
        FakeMetaClient,
    )

    response = admin_client.post(
        "/admin/integrations/whatsapp/test",
        data={"to_phone": "5511777777777", "message": "Teste SIST-iONM"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert calls == [
        {
            "api_version": "v23.0",
            "phone_number_id": "123456789",
            "access_token": "EAAB-TEST",
            "to_phone": "5511777777777",
            "message": "Teste SIST-iONM",
        },
    ]
    page = admin_client.get("/admin/integrations/whatsapp")
    assert "Teste enviado" in page.text
    assert "EAAB-TEST" not in page.text
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        status = connection.execute(
            "SELECT last_test_status FROM whatsapp_settings WHERE id=1",
        ).fetchone()[0]
    assert status == "success"

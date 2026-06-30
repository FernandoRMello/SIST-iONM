import sqlite3

from fastapi.testclient import TestClient

from tests.conftest import LegacyTestState


def test_access_profiles_page_is_admin_only(
    authenticated_client: TestClient,
    admin_client: TestClient,
) -> None:
    denied = authenticated_client.get("/admin/access-profiles")
    allowed = admin_client.get("/admin/access-profiles")

    assert denied.status_code == 403
    assert allowed.status_code == 200
    assert "Perfis de acesso" in allowed.text
    assert "access.manage" in allowed.text


def test_admin_can_create_profile_and_enable_permission(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    created = admin_client.post(
        "/admin/access-profiles",
        data={"name": "Auditoria QA", "description": "Perfil de auditoria"},
        follow_redirects=False,
    )

    assert created.status_code == 303
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        connection.row_factory = sqlite3.Row
        profile = connection.execute(
            "SELECT id FROM access_profiles WHERE name=?",
            ("Auditoria QA",),
        ).fetchone()
        permission = connection.execute(
            "SELECT id FROM access_permissions WHERE code=?",
            ("finance.sensitive.view",),
        ).fetchone()

    saved = admin_client.post(
        "/admin/access-profiles/permissions",
        data={f"perm_{profile['id']}_{permission['id']}": "Sim"},
        follow_redirects=False,
    )

    assert saved.status_code == 303
    page = admin_client.get("/admin/access-profiles")
    assert "Auditoria QA" in page.text
    assert "finance.sensitive.view" in page.text


def test_admin_can_assign_access_profile_to_user(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        connection.row_factory = sqlite3.Row
        profile = connection.execute(
            "SELECT id FROM access_profiles WHERE name='RH'",
        ).fetchone()

    response = admin_client.post(
        f"/settings/users/{legacy_test_state.ids['settings_user_id']}/profiles",
        data={f"profile_{profile['id']}": "Sim"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM user_access_profiles WHERE user_id=? AND profile_id=?",
            (legacy_test_state.ids["settings_user_id"], profile["id"]),
        ).fetchone()[0]
    assert count == 1

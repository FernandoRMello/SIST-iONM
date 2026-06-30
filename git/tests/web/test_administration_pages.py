import re
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from tests.conftest import LegacyTestState

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = REPO_ROOT / "app" / "templates"
SHARED_STATIC = REPO_ROOT / "app" / "shared" / "web" / "static"


def test_administration_templates_use_accessible_shared_contracts() -> None:
    sources = {
        name: (TEMPLATES / name).read_text(encoding="utf-8")
        for name in ("crud.html", "settings.html", "permissions.html")
    }

    for name, source in sources.items():
        assert "page_header" in source, name
        assert not re.search(r"\son(?:click|change|submit|input)=", source, re.IGNORECASE), name

    assert "data-table-search" in sources["crud.html"]
    assert "empty_state" in sources["crud.html"]
    assert "data-confirm" in sources["crud.html"]
    assert "for=\"field-{{ key }}\"" in sources["crud.html"]

    for heading in (
        "Empresa e impressão",
        "Usuários e acesso",
        "E-mails por perfil",
        "Backup e restauração",
    ):
        assert heading in sources["settings.html"]
    assert not re.search(
        r'type="password"[^>]*value=',
        sources["settings.html"],
        re.IGNORECASE,
    )

    assert "aria-label" in sources["permissions.html"]
    assert "ui-permission-matrix" in sources["permissions.html"]


def test_administration_scripts_are_local_and_progressive() -> None:
    forms = (SHARED_STATIC / "js" / "forms.js").read_text(encoding="utf-8")
    tables = (SHARED_STATIC / "js" / "tables.js").read_text(encoding="utf-8")

    for snippet in ("data-confirm", "data-disclosure"):
        assert snippet in forms
    assert "data-table-search" in tables
    assert "textContent" in tables
    assert "innerHTML" not in forms + tables


def test_administration_surfaces_render_for_admin(admin_client: TestClient) -> None:
    expectations = {
        "/cadastros/clients": ("Clientes", "Nome/Razão Social"),
        "/cadastros/suppliers": ("Fornecedores", "Condição comercial"),
        "/cadastros/sellers": ("Vendedores", "% Comissão"),
        "/cadastros/products": ("Produtos", "Preço Mínimo"),
        "/settings": ("Configurações", "Usuários e acesso"),
        "/admin/permissions": ("Permissões", "Administração de perfis"),
    }

    for path, snippets in expectations.items():
        response = admin_client.get(path)
        assert response.status_code == 200, path
        for snippet in snippets:
            assert snippet in response.text, (path, snippet)


def test_settings_never_render_stored_smtp_password(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    secret = "SMTP-SECRET-MUST-NOT-LEAK"
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        connection.execute(
            "UPDATE role_email_settings SET smtp_password=? WHERE id=(SELECT MIN(id) FROM role_email_settings)",
            (secret,),
        )
        connection.commit()

    response = admin_client.get("/settings")

    assert response.status_code == 200
    assert secret not in response.text
    assert re.search(r'type="password"[^>]*value=""', response.text) is None


def test_blank_smtp_password_preserves_existing_secret(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    secret = "SMTP-SECRET-TO-PRESERVE"
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT * FROM role_email_settings ORDER BY id LIMIT 1"
        ).fetchone()
        connection.execute(
            "UPDATE role_email_settings SET smtp_password=? WHERE id=?",
            (secret, row["id"]),
        )
        connection.commit()

    response = admin_client.post(
        "/settings/role-email/save",
        data={
            f"email_from_{row['id']}": row["email_from"] or "",
            f"smtp_host_{row['id']}": row["smtp_host"] or "",
            f"smtp_port_{row['id']}": row["smtp_port"] or "",
            f"smtp_user_{row['id']}": row["smtp_user"] or "",
            f"smtp_password_{row['id']}": "",
            f"signature_{row['id']}": row["signature"] or "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        saved = connection.execute(
            "SELECT smtp_password FROM role_email_settings WHERE id=?",
            (row["id"],),
        ).fetchone()[0]
    assert saved == secret


def test_creating_user_persists_email_and_profile(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    response = admin_client.post(
        "/settings/users/create",
        data={
            "username": "new.user.qa",
            "email": "new.user.qa@example.invalid",
            "password": "Temporary!123",
            "role": "vendedor",
            "seller_id": "",
            "active": "Sim",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        connection.row_factory = sqlite3.Row
        account = connection.execute(
            "SELECT id, email FROM users WHERE username=?",
            ("new.user.qa",),
        ).fetchone()
        profile = connection.execute(
            "SELECT email FROM user_profiles WHERE user_id=?",
            (account["id"],),
        ).fetchone()
    assert account["email"] == "new.user.qa@example.invalid"
    assert profile["email"] == "new.user.qa@example.invalid"

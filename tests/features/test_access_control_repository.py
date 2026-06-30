import sqlite3
from pathlib import Path

from app.features.access_control.repository import AccessControlRepository


def _prepare_database(path: Path) -> AccessControlRepository:
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                password_hash TEXT,
                role TEXT,
                active TEXT
            )
            """,
        )
        connection.execute(
            "INSERT INTO users(username,password_hash,role,active) VALUES(?,?,?,?)",
            ("admin.qa", "hash", "admin", "Sim"),
        )
        connection.execute(
            "INSERT INTO users(username,password_hash,role,active) VALUES(?,?,?,?)",
            ("rh.qa", "hash", "vendedor", "Sim"),
        )
        connection.commit()
    repository = AccessControlRepository(path)
    repository.init_schema()
    repository.ensure_seed_data()
    return repository


def test_seed_profiles_and_permissions_are_created(tmp_path: Path) -> None:
    repository = _prepare_database(tmp_path / "access.db")

    profiles = repository.profiles()
    permissions = repository.permissions()

    assert {profile["name"] for profile in profiles} >= {"Admin", "RH", "Vendedor"}
    assert {permission["code"] for permission in permissions} >= {
        "access.manage",
        "users.manage",
        "hr.payroll.view",
        "whatsapp.configure",
    }


def test_profile_assignment_grants_permission(tmp_path: Path) -> None:
    repository = _prepare_database(tmp_path / "access.db")
    profile_id = repository.create_profile(
        name="Gestor QA",
        description="Perfil customizado para QA",
    )
    permission_id = repository.permission_by_code("hr.view")["id"]
    repository.set_profile_permission(
        profile_id=profile_id,
        permission_id=permission_id,
        enabled=True,
        scope="all",
    )

    repository.assign_profile(user_id=2, profile_id=profile_id, assigned_by_user_id=1)

    assert repository.user_has_permission(2, "hr.view", legacy_role="vendedor") is True
    assert repository.user_has_permission(2, "access.manage", legacy_role="vendedor") is False


def test_admin_legacy_role_is_safe_fallback(tmp_path: Path) -> None:
    repository = _prepare_database(tmp_path / "access.db")

    assert repository.user_has_permission(999, "access.manage", legacy_role="admin") is True
    assert repository.user_has_permission(999, "access.manage", legacy_role="vendedor") is False

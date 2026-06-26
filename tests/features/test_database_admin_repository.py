import sqlite3
from pathlib import Path

from app.features.database_admin.repository import DatabaseSettingsRepository
from app.features.database_admin.security import (
    decrypt_database_password,
    encrypt_database_password,
)


def test_database_password_is_encrypted_and_decrypted() -> None:
    encrypted = encrypt_database_password("pg-secret", "test-master-key")

    assert encrypted
    assert encrypted != "pg-secret"
    assert decrypt_database_password(encrypted, "test-master-key") == "pg-secret"
    assert decrypt_database_password(encrypted, "wrong-key") == ""


def test_database_config_preserves_password_and_masks_view(tmp_path: Path) -> None:
    repository = DatabaseSettingsRepository(tmp_path / "settings.db")

    repository.save_config(
        name="Servidor local",
        engine="postgresql",
        host="127.0.0.1",
        port=5432,
        database_name="sist_ionm",
        username="sist_ionm",
        password="first-secret",
        ssl_mode="prefer",
        notes="Banco local Ubuntu",
        updated_by_user_id=1,
        master_key="test-master-key",
    )
    first_view = repository.get_config_for_view()
    first_secret = repository.get_password(master_key="test-master-key")

    repository.save_config(
        name="Servidor local atualizado",
        engine="postgresql",
        host="db.internal",
        port=5433,
        database_name="sist_ionm_prod",
        username="app_user",
        password="",
        ssl_mode="require",
        notes="Preservar senha",
        updated_by_user_id=2,
        master_key="test-master-key",
    )

    view = repository.get_config_for_view()

    assert first_secret == "first-secret"
    assert view["name"] == "Servidor local atualizado"
    assert view["host"] == "db.internal"
    assert view["port"] == 5433
    assert view["password_status"] == "Configurada"
    assert "first-secret" not in str(view)
    assert repository.get_password(master_key="test-master-key") == "first-secret"
    assert first_view["password_status"] == "Configurada"


def test_database_repository_records_test_and_prepare_results(tmp_path: Path) -> None:
    repository = DatabaseSettingsRepository(tmp_path / "settings.db")
    repository.save_config(
        name="Servidor local",
        engine="postgresql",
        host="127.0.0.1",
        port=5432,
        database_name="sist_ionm",
        username="sist_ionm",
        password="secret",
        ssl_mode="prefer",
        notes="",
        updated_by_user_id=1,
        master_key="test-master-key",
    )

    repository.record_test_result(status="success", message="Conexão realizada com sucesso.")
    repository.record_prepare_result(status="error", message="Permissão CREATE ausente.")

    with sqlite3.connect(repository.database_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute("SELECT * FROM database_connections WHERE id=1").fetchone()

    assert row["last_test_status"] == "success"
    assert row["last_test_message"] == "Conexão realizada com sucesso."
    assert row["last_test_at"]
    assert row["last_prepare_status"] == "error"
    assert row["last_prepare_message"] == "Permissão CREATE ausente."
    assert row["last_prepare_at"]

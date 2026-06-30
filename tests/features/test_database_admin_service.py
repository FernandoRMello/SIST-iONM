from dataclasses import dataclass

from app.features.database_admin.service import (
    DatabaseAdminService,
    OperationResult,
    build_connection_parameters,
    safe_database_error_message,
)


class FakeCursor:
    def __init__(self):
        self.queries: list[str] = []

    def execute(self, query: str, params: tuple = ()) -> None:
        self.queries.append(query)

    def fetchone(self):
        return (1,)


class FakeConnection:
    def __init__(self):
        self.cursor_instance = FakeCursor()
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self.cursor_instance

    def commit(self) -> None:
        self.committed = True


@dataclass
class FakeConnector:
    connection: FakeConnection

    def __call__(self, **kwargs):
        self.kwargs = kwargs
        return self.connection


def _config() -> dict:
    return {
        "host": "127.0.0.1",
        "port": 5432,
        "database_name": "sist_ionm",
        "username": "sist_ionm",
        "ssl_mode": "prefer",
    }


def test_build_connection_parameters_never_include_plain_dsn() -> None:
    params = build_connection_parameters(_config(), "pg-secret")

    assert params == {
        "host": "127.0.0.1",
        "port": 5432,
        "dbname": "sist_ionm",
        "user": "sist_ionm",
        "password": "pg-secret",
        "sslmode": "prefer",
        "connect_timeout": 5,
    }
    assert "pg-secret" not in repr(params.keys())


def test_service_tests_connection_with_select_one() -> None:
    connection = FakeConnection()
    connector = FakeConnector(connection)
    service = DatabaseAdminService(connector=connector)

    result = service.test_connection(_config(), "pg-secret")

    assert result == OperationResult(status="success", message="Conexão realizada com sucesso.")
    assert connector.kwargs["password"] == "pg-secret"
    assert connection.cursor_instance.queries == ["SELECT 1"]


def test_service_prepares_environment_with_control_table() -> None:
    connection = FakeConnection()
    service = DatabaseAdminService(connector=FakeConnector(connection))

    result = service.prepare_environment(_config(), "pg-secret")

    assert result.status == "success"
    assert result.message == "Ambiente PostgreSQL preparado para migração/cutover."
    assert any("CREATE TABLE IF NOT EXISTS sist_ionm_schema_status" in query for query in connection.cursor_instance.queries)
    assert any("INSERT INTO sist_ionm_schema_status" in query for query in connection.cursor_instance.queries)
    assert connection.committed is True


def test_safe_database_error_message_hides_secrets() -> None:
    message = safe_database_error_message(Exception("password pg-secret authentication failed"))

    assert message == "Falha de autenticação no banco de dados."
    assert "pg-secret" not in message


def test_service_returns_safe_error_when_connection_fails() -> None:
    def failing_connector(**kwargs):
        raise TimeoutError("could not connect with password pg-secret")

    service = DatabaseAdminService(connector=failing_connector)

    result = service.test_connection(_config(), "pg-secret")

    assert result.status == "error"
    assert result.message == "Servidor não encontrado ou porta indisponível."
    assert "pg-secret" not in result.message


def test_service_reports_missing_postgresql_driver_without_breaking_import() -> None:
    def missing_driver_connector(**kwargs):
        raise ModuleNotFoundError("No module named 'psycopg'")

    service = DatabaseAdminService(connector=missing_driver_connector)

    result = service.test_connection(_config(), "pg-secret")

    assert result == OperationResult(
        status="error",
        message="Driver PostgreSQL não instalado no ambiente.",
    )

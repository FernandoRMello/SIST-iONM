import sqlite3

import pytest

import app.main as legacy
from tests.conftest import LegacyTestState


def test_database_context_closes_connection(
    legacy_test_state: LegacyTestState,
) -> None:
    with legacy.db() as connection:
        assert connection.execute("SELECT 1").fetchone()[0] == 1

    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connection.execute("SELECT 1")

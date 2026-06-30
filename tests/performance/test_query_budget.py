import sqlite3

import pytest
from fastapi.testclient import TestClient

import app.main as legacy
from tests.conftest import LegacyTestState


def count_queries(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> tuple[int, int]:
    original_q = legacy.q
    calls = 0

    def counted_q(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original_q(*args, **kwargs)

    monkeypatch.setattr(legacy, "q", counted_q)
    response = client.get(path)
    return response.status_code, calls


def seed_opportunities(database_path, amount: int) -> None:
    with sqlite3.connect(database_path) as connection:
        base = connection.execute(
            "SELECT client_id,supplier_id,seller_id,created_by FROM opportunities ORDER BY id LIMIT 1"
        ).fetchone()
        for index in range(amount):
            connection.execute(
                """
                INSERT INTO opportunities(
                    ro_number,created_at,client_id,supplier_id,seller_id,status,
                    probability,forecast_date,next_followup,payment_terms,notes,created_by
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    f"RO-PERF-{index:04d}",
                    "2026-06-18",
                    base[0],
                    base[1],
                    base[2],
                    "Lead",
                    50,
                    "2026-07-01",
                    "2026-06-25",
                    "PIX",
                    "Carga de desempenho",
                    base[3],
                ),
            )
        connection.commit()


@pytest.mark.parametrize(
    ("path", "budget"),
    [("/", 6), ("/opportunities", 8), ("/chat", 8)],
)
def test_page_query_count_does_not_grow_with_rows(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    budget: int,
) -> None:
    status, baseline = count_queries(admin_client, monkeypatch, path)
    assert status == 200

    seed_opportunities(legacy_test_state.database_path, 20)
    status, expanded = count_queries(admin_client, monkeypatch, path)

    assert status == 200
    assert expanded <= budget
    assert expanded <= baseline + 1

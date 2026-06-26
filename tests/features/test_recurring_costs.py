import sqlite3
from datetime import date

from app.features.finance.calendar import calculate_due_date
from app.features.finance.recurring_costs import (
    ensure_recurring_cost_schema,
    generate_due_recurring_costs,
)


def test_due_date_uses_month_end_and_next_business_day() -> None:
    assert calculate_due_date("2026-02", 31, set()) == date(2026, 3, 2)
    assert calculate_due_date("2026-08", 15, set()) == date(2026, 8, 17)


def test_due_date_skips_registered_holidays() -> None:
    holidays = {date(2026, 6, 15), date(2026, 6, 16)}
    assert calculate_due_date("2026-06", 15, holidays) == date(2026, 6, 17)


def test_generator_creates_one_payable_per_cost_and_period() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE payables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id INTEGER, seller_id INTEGER, description TEXT, category TEXT,
            amount REAL, issue_date TEXT, due_date TEXT, status TEXT,
            payment_method TEXT, bank_account TEXT, notes TEXT
        )
        """
    )
    ensure_recurring_cost_schema(connection)
    category_id = connection.execute(
        "INSERT INTO cost_categories(name, active, created_at) VALUES('Aluguel','Sim','2026-06-01')"
    ).lastrowid
    cost_id = connection.execute(
        """
        INSERT INTO recurring_costs(
            description, category_id, cost_center, amount, due_day, start_date,
            status, payment_method, bank_account, created_at, updated_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            "Aluguel sede", category_id, "Administrativo", 1500, 10,
            "2026-06-01", "Ativo", "Boleto", "Principal",
            "2026-06-01", "2026-06-01",
        ),
    ).lastrowid
    connection.commit()

    first = generate_due_recurring_costs(connection, date(2026, 6, 26), 1)
    second = generate_due_recurring_costs(connection, date(2026, 6, 26), 1)

    assert first["created"] == 1
    assert second["created"] == 0
    payable = dict(connection.execute("SELECT * FROM payables").fetchone())
    assert payable["description"] == "Aluguel sede · 2026-06"
    assert payable["amount"] == 1500
    assert payable["due_date"] == "2026-06-10"
    occurrence = connection.execute(
        "SELECT recurring_cost_id, period, payable_id FROM recurring_cost_occurrences"
    ).fetchone()
    assert tuple(occurrence) == (cost_id, "2026-06", payable["id"])


def test_generator_respects_vigency_and_preserves_generated_value() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE payables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id INTEGER, seller_id INTEGER, description TEXT, category TEXT,
            amount REAL, issue_date TEXT, due_date TEXT, status TEXT,
            payment_method TEXT, bank_account TEXT, notes TEXT
        )
        """
    )
    ensure_recurring_cost_schema(connection)
    category_id = connection.execute(
        "INSERT INTO cost_categories(name, active, created_at) VALUES('Licença','Sim','2026-01-01')"
    ).lastrowid
    connection.execute(
        """
        INSERT INTO recurring_costs(
            description, category_id, amount, due_day, start_date, end_date,
            status, created_at, updated_at
        ) VALUES('ERP', ?, 200, 5, '2026-06-01', '2026-07-31', 'Ativo', '2026-01-01', '2026-01-01')
        """,
        (category_id,),
    )
    connection.commit()

    assert generate_due_recurring_costs(connection, date(2026, 5, 20), 1)["created"] == 0
    assert generate_due_recurring_costs(connection, date(2026, 6, 20), 1)["created"] == 1
    connection.execute("UPDATE recurring_costs SET amount=250")
    connection.commit()
    assert generate_due_recurring_costs(connection, date(2026, 6, 21), 1)["created"] == 0
    assert connection.execute("SELECT amount FROM payables").fetchone()[0] == 200
    assert generate_due_recurring_costs(connection, date(2026, 8, 1), 1)["created"] == 1
    assert connection.execute(
        "SELECT COUNT(*) FROM recurring_cost_occurrences WHERE period='2026-08'"
    ).fetchone()[0] == 0


def test_generator_backfills_months_missed_while_server_was_off() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE payables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id INTEGER, seller_id INTEGER, description TEXT, category TEXT,
            amount REAL, issue_date TEXT, due_date TEXT, status TEXT,
            payment_method TEXT, bank_account TEXT, notes TEXT
        )
        """
    )
    ensure_recurring_cost_schema(connection)
    category_id = connection.execute(
        "INSERT INTO cost_categories(name,active,created_at) VALUES('Servidor','Sim','2026-01-01')"
    ).lastrowid
    connection.execute(
        """
        INSERT INTO recurring_costs(
            description,category_id,amount,due_day,start_date,status,created_at,updated_at
        ) VALUES('Nuvem',?,100,10,'2026-01-01','Ativo','2026-01-01','2026-01-01')
        """,
        (category_id,),
    )
    connection.commit()

    result = generate_due_recurring_costs(connection, date(2026, 3, 20), 1)

    assert result["created"] == 3
    periods = connection.execute(
        "SELECT period FROM recurring_cost_occurrences ORDER BY period"
    ).fetchall()
    assert [row[0] for row in periods] == ["2026-01", "2026-02", "2026-03"]

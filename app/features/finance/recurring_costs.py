from datetime import date, datetime
from sqlite3 import Connection

from app.features.finance.calendar import calculate_due_date


def _periods_between(start_date: str, end_date: date, configured_end: str | None):
    year, month = map(int, start_date[:7].split("-"))
    end_period = end_date.strftime("%Y-%m")
    configured_end_period = configured_end[:7] if configured_end else None
    while f"{year:04d}-{month:02d}" <= end_period:
        period = f"{year:04d}-{month:02d}"
        if configured_end_period and period > configured_end_period:
            break
        yield period
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1


def ensure_recurring_cost_schema(connection: Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS cost_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            active TEXT NOT NULL DEFAULT 'Sim',
            created_by_user_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            deleted_at TEXT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ux_cost_categories_active_name
        ON cost_categories(name) WHERE deleted_at IS NULL;

        CREATE TABLE IF NOT EXISTS recurring_costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            supplier_id INTEGER,
            seller_id INTEGER,
            vendor TEXT,
            cost_center TEXT,
            amount REAL NOT NULL,
            due_day INTEGER NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT,
            payment_method TEXT,
            bank_account TEXT,
            notes TEXT,
            status TEXT NOT NULL DEFAULT 'Ativo',
            created_by_user_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            deleted_at TEXT
        );

        CREATE TABLE IF NOT EXISTS business_holidays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            holiday_date TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL,
            created_by_user_id INTEGER,
            created_at TEXT NOT NULL,
            deleted_at TEXT
        );

        CREATE TABLE IF NOT EXISTS recurring_cost_occurrences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recurring_cost_id INTEGER NOT NULL,
            period TEXT NOT NULL,
            payable_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            due_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(recurring_cost_id, period)
        );

        CREATE TABLE IF NOT EXISTS recurring_cost_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period TEXT NOT NULL,
            run_date TEXT NOT NULL,
            created_count INTEGER NOT NULL DEFAULT 0,
            error_count INTEGER NOT NULL DEFAULT 0,
            actor_user_id INTEGER,
            details TEXT
        );
        """
    )
    columns = {row[1] for row in connection.execute("PRAGMA table_info(payables)")}
    for name, column_type in (
        ("recurring_cost_id", "INTEGER"),
        ("recurring_period", "TEXT"),
    ):
        if name not in columns:
            connection.execute(f"ALTER TABLE payables ADD COLUMN {name} {column_type}")
    connection.commit()


def generate_due_recurring_costs(
    connection: Connection,
    today_date: date,
    actor_user_id: int | None,
) -> dict[str, int]:
    ensure_recurring_cost_schema(connection)
    current_period = today_date.strftime("%Y-%m")
    holidays = {
        date.fromisoformat(row[0])
        for row in connection.execute(
            "SELECT holiday_date FROM business_holidays WHERE deleted_at IS NULL"
        )
    }
    rows = connection.execute(
        """
        SELECT rc.*, cc.name AS category_name
        FROM recurring_costs rc
        JOIN cost_categories cc ON cc.id=rc.category_id
        WHERE rc.status='Ativo' AND rc.deleted_at IS NULL
          AND rc.start_date <= ?
          AND (rc.end_date IS NULL OR rc.end_date='' OR rc.end_date >= rc.start_date)
        """,
        (today_date.isoformat(),),
    ).fetchall()
    created = 0
    errors = 0
    now = datetime.now().isoformat(timespec="seconds")
    for row in rows:
        for period in _periods_between(row["start_date"], today_date, row["end_date"]):
            try:
                if connection.execute(
                    "SELECT 1 FROM recurring_cost_occurrences WHERE recurring_cost_id=? AND period=?",
                    (row["id"], period),
                ).fetchone():
                    continue
                connection.execute("SAVEPOINT recurring_occurrence")
                due_date = calculate_due_date(period, int(row["due_day"]), holidays)
                cursor = connection.execute(
                    """
                    INSERT INTO payables(
                        supplier_id,seller_id,description,category,amount,issue_date,due_date,
                        status,payment_method,bank_account,notes,recurring_cost_id,recurring_period
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        row["supplier_id"], row["seller_id"],
                        f"{row['description']} · {period}", row["category_name"], row["amount"],
                        today_date.isoformat(), due_date.isoformat(), "Aberto",
                        row["payment_method"], row["bank_account"], row["notes"], row["id"], period,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO recurring_cost_occurrences(
                        recurring_cost_id,period,payable_id,amount,due_date,created_at
                    ) VALUES(?,?,?,?,?,?)
                    """,
                    (row["id"], period, cursor.lastrowid, row["amount"], due_date.isoformat(), now),
                )
                connection.execute("RELEASE SAVEPOINT recurring_occurrence")
                created += 1
            except Exception:
                connection.execute("ROLLBACK TO SAVEPOINT recurring_occurrence")
                connection.execute("RELEASE SAVEPOINT recurring_occurrence")
                errors += 1
    connection.execute(
        """
        INSERT INTO recurring_cost_runs(
            period,run_date,created_count,error_count,actor_user_id,details
        ) VALUES(?,?,?,?,?,?)
        """,
        (
            current_period, today_date.isoformat(), created, errors, actor_user_id,
            "Geração automática mensal",
        ),
    )
    connection.commit()
    return {"created": created, "errors": errors}

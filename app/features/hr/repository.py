import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


class HRRepository:
    def __init__(self, database_path: Path | str):
        self.database_path = Path(database_path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def init_schema(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS hr_employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    full_name TEXT,
                    document TEXT,
                    email TEXT,
                    phone TEXT,
                    department_id INTEGER,
                    job_title TEXT,
                    contract_type TEXT,
                    admission_date TEXT,
                    status TEXT DEFAULT 'Ativo',
                    base_salary REAL DEFAULT 0,
                    manager_user_id INTEGER,
                    notes TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
                """,
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS hr_commission_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    employee_id INTEGER,
                    profile_id INTEGER,
                    basis TEXT,
                    calculation_scope TEXT,
                    percentage_type TEXT,
                    fixed_percentage REAL DEFAULT 0,
                    is_active TEXT DEFAULT 'Sim',
                    created_at TEXT,
                    updated_at TEXT
                )
                """,
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS hr_commission_tiers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_id INTEGER,
                    min_value REAL DEFAULT 0,
                    max_value REAL,
                    percentage REAL DEFAULT 0
                )
                """,
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS hr_benefit_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    employee_id INTEGER,
                    profile_id INTEGER,
                    benefit_type TEXT,
                    basis TEXT,
                    calculation_scope TEXT,
                    fixed_amount REAL DEFAULT 0,
                    percentage REAL DEFAULT 0,
                    target_value REAL DEFAULT 0,
                    is_active TEXT DEFAULT 'Sim',
                    created_at TEXT,
                    updated_at TEXT
                )
                """,
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS hr_payroll_periods (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    period TEXT UNIQUE,
                    status TEXT,
                    created_by_user_id INTEGER,
                    approved_by_user_id INTEGER,
                    paid_by_user_id INTEGER,
                    created_at TEXT,
                    approved_at TEXT,
                    paid_at TEXT
                )
                """,
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS hr_payroll_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payroll_period_id INTEGER,
                    employee_id INTEGER,
                    item_type TEXT,
                    description TEXT,
                    basis_amount REAL DEFAULT 0,
                    percentage REAL DEFAULT 0,
                    amount REAL DEFAULT 0,
                    source_type TEXT,
                    source_id INTEGER,
                    created_at TEXT
                )
                """,
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS hr_payment_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payroll_period_id INTEGER,
                    employee_id INTEGER,
                    amount REAL DEFAULT 0,
                    status TEXT,
                    paid_at TEXT,
                    notes TEXT
                )
                """,
            )
            connection.commit()

    def create_employee(
        self,
        *,
        full_name: str,
        document: str,
        email: str,
        phone: str,
        department_id: int | None,
        job_title: str,
        contract_type: str,
        admission_date: str,
        status: str,
        base_salary: float,
        user_id: int | None,
        manager_user_id: int | None,
        notes: str,
    ) -> int:
        self.init_schema()
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO hr_employees(
                    user_id, full_name, document, email, phone, department_id,
                    job_title, contract_type, admission_date, status, base_salary,
                    manager_user_id, notes, created_at, updated_at
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    user_id,
                    full_name.strip(),
                    document.strip(),
                    email.strip(),
                    phone.strip(),
                    department_id,
                    job_title.strip(),
                    contract_type.strip() or "CLT",
                    admission_date,
                    status or "Ativo",
                    float(base_salary or 0),
                    manager_user_id,
                    notes.strip(),
                    now,
                    now,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def employee(self, employee_id: int) -> dict[str, Any] | None:
        self.init_schema()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM hr_employees WHERE id=?",
                (employee_id,),
            ).fetchone()
        return dict(row) if row else None

    def employees(self) -> list[dict[str, Any]]:
        self.init_schema()
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM hr_employees ORDER BY full_name",
            ).fetchall()
        return [dict(row) for row in rows]

    def create_commission_rule(
        self,
        *,
        name: str,
        employee_id: int | None,
        profile_id: int | None,
        basis: str,
        calculation_scope: str,
        percentage_type: str,
        fixed_percentage: float,
        is_active: bool,
    ) -> int:
        self.init_schema()
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO hr_commission_rules(
                    name, employee_id, profile_id, basis, calculation_scope,
                    percentage_type, fixed_percentage, is_active, created_at, updated_at
                )
                VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    name.strip(),
                    employee_id,
                    profile_id,
                    basis,
                    calculation_scope,
                    percentage_type,
                    float(fixed_percentage or 0),
                    "Sim" if is_active else "Não",
                    now,
                    now,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def create_benefit_rule(
        self,
        *,
        name: str,
        employee_id: int | None,
        profile_id: int | None,
        benefit_type: str,
        basis: str,
        calculation_scope: str,
        fixed_amount: float,
        percentage: float,
        target_value: float,
        is_active: bool,
    ) -> int:
        self.init_schema()
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO hr_benefit_rules(
                    name, employee_id, profile_id, benefit_type, basis,
                    calculation_scope, fixed_amount, percentage, target_value,
                    is_active, created_at, updated_at
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    name.strip(),
                    employee_id,
                    profile_id,
                    benefit_type,
                    basis,
                    calculation_scope,
                    float(fixed_amount or 0),
                    float(percentage or 0),
                    float(target_value or 0),
                    "Sim" if is_active else "Não",
                    now,
                    now,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def commission_rules(self) -> list[dict[str, Any]]:
        self.init_schema()
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM hr_commission_rules ORDER BY id DESC",
            ).fetchall()
        return [dict(row) for row in rows]

    def benefit_rules(self) -> list[dict[str, Any]]:
        self.init_schema()
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM hr_benefit_rules ORDER BY id DESC",
            ).fetchall()
        return [dict(row) for row in rows]

    def payroll_periods(self) -> list[dict[str, Any]]:
        self.init_schema()
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM hr_payroll_periods ORDER BY period DESC",
            ).fetchall()
        return [dict(row) for row in rows]

    def _company_basis_total(self, basis: str, period: str) -> float:
        column = "overprice" if basis == "profit" else "total_amount"
        with self.connect() as connection:
            try:
                row = connection.execute(
                    f"""
                    SELECT COALESCE(SUM({column}), 0) AS total
                    FROM orders
                    WHERE substr(COALESCE(created_at,''), 1, 7)=?
                    """,
                    (period,),
                ).fetchone()
            except sqlite3.OperationalError:
                return 0.0
        return float(row["total"] or 0)

    def generate_payroll_period(self, *, period: str, created_by_user_id: int) -> int:
        self.init_schema()
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO hr_payroll_periods(period,status,created_by_user_id,created_at)
                VALUES(?,?,?,?)
                ON CONFLICT(period) DO UPDATE SET status=hr_payroll_periods.status
                """,
                (period, "Rascunho", created_by_user_id, now),
            )
            row = connection.execute(
                "SELECT id FROM hr_payroll_periods WHERE period=?",
                (period,),
            ).fetchone()
            period_id = int(row["id"] if row else cursor.lastrowid)
            connection.execute(
                "DELETE FROM hr_payroll_items WHERE payroll_period_id=?",
                (period_id,),
            )
            employees = connection.execute(
                "SELECT * FROM hr_employees WHERE status='Ativo' ORDER BY id",
            ).fetchall()
            commission_rules = connection.execute(
                "SELECT * FROM hr_commission_rules WHERE is_active='Sim'",
            ).fetchall()
            benefit_rules = connection.execute(
                "SELECT * FROM hr_benefit_rules WHERE is_active='Sim'",
            ).fetchall()
            for employee in employees:
                self._insert_item(
                    connection,
                    period_id,
                    int(employee["id"]),
                    "salary",
                    "Salário base",
                    float(employee["base_salary"] or 0),
                    0,
                    float(employee["base_salary"] or 0),
                    "employee",
                    int(employee["id"]),
                    now,
                )
                for benefit in benefit_rules:
                    if benefit["employee_id"] and int(benefit["employee_id"]) != int(employee["id"]):
                        continue
                    amount = float(benefit["fixed_amount"] or 0)
                    if not amount and float(benefit["percentage"] or 0):
                        basis_amount = self._company_basis_total(str(benefit["basis"]), period)
                        amount = basis_amount * float(benefit["percentage"] or 0) / 100
                    self._insert_item(
                        connection,
                        period_id,
                        int(employee["id"]),
                        "benefit",
                        str(benefit["name"]),
                        float(benefit["fixed_amount"] or 0),
                        float(benefit["percentage"] or 0),
                        amount,
                        "benefit_rule",
                        int(benefit["id"]),
                        now,
                    )
                for rule in commission_rules:
                    if rule["employee_id"] and int(rule["employee_id"]) != int(employee["id"]):
                        continue
                    basis_amount = self._company_basis_total(str(rule["basis"]), period)
                    amount = basis_amount * float(rule["fixed_percentage"] or 0) / 100
                    self._insert_item(
                        connection,
                        period_id,
                        int(employee["id"]),
                        "commission",
                        str(rule["name"]),
                        basis_amount,
                        float(rule["fixed_percentage"] or 0),
                        amount,
                        "commission_rule",
                        int(rule["id"]),
                        now,
                    )
            connection.commit()
        return period_id

    def _insert_item(
        self,
        connection: sqlite3.Connection,
        period_id: int,
        employee_id: int,
        item_type: str,
        description: str,
        basis_amount: float,
        percentage: float,
        amount: float,
        source_type: str,
        source_id: int,
        created_at: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO hr_payroll_items(
                payroll_period_id, employee_id, item_type, description,
                basis_amount, percentage, amount, source_type, source_id, created_at
            )
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                period_id,
                employee_id,
                item_type,
                description,
                basis_amount,
                percentage,
                amount,
                source_type,
                source_id,
                created_at,
            ),
        )

    def payroll_items(self, period_id: int) -> list[dict[str, Any]]:
        self.init_schema()
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT item.*, employee.full_name
                FROM hr_payroll_items item
                JOIN hr_employees employee ON employee.id = item.employee_id
                WHERE item.payroll_period_id=?
                ORDER BY employee.full_name, item.id
                """,
                (period_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def set_payroll_status(self, *, period_id: int, status: str, user_id: int) -> None:
        column_user = {
            "Aprovada": "approved_by_user_id",
            "Paga": "paid_by_user_id",
        }.get(status)
        column_at = {
            "Aprovada": "approved_at",
            "Paga": "paid_at",
        }.get(status)
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            if column_user and column_at:
                connection.execute(
                    f"UPDATE hr_payroll_periods SET status=?, {column_user}=?, {column_at}=? WHERE id=?",
                    (status, user_id, now, period_id),
                )
            else:
                connection.execute(
                    "UPDATE hr_payroll_periods SET status=? WHERE id=?",
                    (status, period_id),
                )
            if status == "Paga":
                rows = connection.execute(
                    """
                    SELECT employee_id, COALESCE(SUM(amount),0) AS total
                    FROM hr_payroll_items
                    WHERE payroll_period_id=?
                    GROUP BY employee_id
                    """,
                    (period_id,),
                ).fetchall()
                for row in rows:
                    connection.execute(
                        """
                        INSERT INTO hr_payment_history(
                            payroll_period_id, employee_id, amount, status, paid_at, notes
                        )
                        VALUES(?,?,?,?,?,?)
                        """,
                        (period_id, row["employee_id"], row["total"], "Pago", now, ""),
                    )
            connection.commit()

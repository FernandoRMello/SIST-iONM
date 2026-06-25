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
                CREATE TABLE IF NOT EXISTS sellers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    username TEXT,
                    email TEXT,
                    phone TEXT,
                    commission_rate REAL DEFAULT 10,
                    active TEXT DEFAULT 'Sim'
                )
                """,
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS hr_employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    seller_id INTEGER,
                    is_seller TEXT DEFAULT 'Não',
                    seller_commission_rate REAL DEFAULT 0,
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
            self._ensure_column(connection, "hr_employees", "seller_id", "INTEGER")
            self._ensure_column(connection, "hr_employees", "is_seller", "TEXT DEFAULT 'Não'")
            self._ensure_column(
                connection,
                "hr_employees",
                "seller_commission_rate",
                "REAL DEFAULT 0",
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
                CREATE TABLE IF NOT EXISTS hr_payroll_adjustment_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    target_contract TEXT,
                    item_type TEXT,
                    basis TEXT,
                    fixed_amount REAL DEFAULT 0,
                    percentage REAL DEFAULT 0,
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

    def _ensure_column(
        self,
        connection: sqlite3.Connection,
        table_name: str,
        column_name: str,
        column_definition: str,
    ) -> None:
        columns = {
            str(row["name"])
            for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        if column_name not in columns:
            connection.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}",
            )

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
        is_seller: bool = False,
        seller_commission_rate: float = 0,
    ) -> int:
        self.init_schema()
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            seller_id = None
            if is_seller:
                seller_id = self._sync_seller(
                    connection,
                    name=full_name,
                    email=email,
                    phone=phone,
                    commission_rate=seller_commission_rate,
                    active=status == "Ativo",
                )
            cursor = connection.execute(
                """
                INSERT INTO hr_employees(
                    user_id, seller_id, is_seller, seller_commission_rate,
                    full_name, document, email, phone, department_id,
                    job_title, contract_type, admission_date, status, base_salary,
                    manager_user_id, notes, created_at, updated_at
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    user_id,
                    seller_id,
                    "Sim" if is_seller else "Não",
                    float(seller_commission_rate or 0),
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

    def _sync_seller(
        self,
        connection: sqlite3.Connection,
        *,
        name: str,
        email: str,
        phone: str,
        commission_rate: float,
        active: bool,
    ) -> int:
        clean_email = email.strip()
        clean_name = name.strip()
        row = None
        if clean_email:
            row = connection.execute(
                "SELECT id FROM sellers WHERE lower(COALESCE(email,''))=lower(?)",
                (clean_email,),
            ).fetchone()
        if row is None:
            row = connection.execute(
                "SELECT id FROM sellers WHERE lower(COALESCE(name,''))=lower(?)",
                (clean_name,),
            ).fetchone()
        active_text = "Sim" if active else "Não"
        if row:
            seller_id = int(row["id"])
            connection.execute(
                """
                UPDATE sellers
                SET name=?, email=?, phone=?, commission_rate=?, active=?
                WHERE id=?
                """,
                (
                    clean_name,
                    clean_email,
                    phone.strip(),
                    float(commission_rate or 0),
                    active_text,
                    seller_id,
                ),
            )
            return seller_id
        cursor = connection.execute(
            """
            INSERT INTO sellers(name,username,email,phone,commission_rate,active)
            VALUES(?,?,?,?,?,?)
            """,
            (
                clean_name,
                "",
                clean_email,
                phone.strip(),
                float(commission_rate or 0),
                active_text,
            ),
        )
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

    def create_payroll_adjustment_rule(
        self,
        *,
        name: str,
        target_contract: str,
        item_type: str,
        basis: str,
        fixed_amount: float,
        percentage: float,
        is_active: bool,
    ) -> int:
        self.init_schema()
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO hr_payroll_adjustment_rules(
                    name, target_contract, item_type, basis, fixed_amount,
                    percentage, is_active, created_at, updated_at
                )
                VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    name.strip(),
                    target_contract.strip() or "CLT",
                    item_type.strip() or "discount",
                    basis.strip() or "base_salary",
                    float(fixed_amount or 0),
                    float(percentage or 0),
                    "Sim" if is_active else "Não",
                    now,
                    now,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def payroll_adjustment_rules(self) -> list[dict[str, Any]]:
        self.init_schema()
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM hr_payroll_adjustment_rules ORDER BY id DESC",
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
            adjustment_rules = connection.execute(
                "SELECT * FROM hr_payroll_adjustment_rules WHERE is_active='Sim'",
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
                for adjustment in adjustment_rules:
                    target = str(adjustment["target_contract"] or "Todos").casefold()
                    contract = str(employee["contract_type"] or "").casefold()
                    if target not in {"todos", "all", contract}:
                        continue
                    basis_amount = self._payroll_basis_amount(
                        connection,
                        period_id,
                        int(employee["id"]),
                        employee,
                        str(adjustment["basis"] or "base_salary"),
                        period,
                    )
                    amount = float(adjustment["fixed_amount"] or 0)
                    percentage = float(adjustment["percentage"] or 0)
                    if percentage:
                        amount += basis_amount * percentage / 100
                    if amount <= 0:
                        continue
                    self._insert_item(
                        connection,
                        period_id,
                        int(employee["id"]),
                        str(adjustment["item_type"] or "discount"),
                        str(adjustment["name"]),
                        basis_amount,
                        percentage,
                        amount,
                        "payroll_adjustment_rule",
                        int(adjustment["id"]),
                        now,
                    )
            connection.commit()
        return period_id

    def _payroll_basis_amount(
        self,
        connection: sqlite3.Connection,
        period_id: int,
        employee_id: int,
        employee: sqlite3.Row,
        basis: str,
        period: str,
    ) -> float:
        if basis == "base_salary":
            return float(employee["base_salary"] or 0)
        if basis in {"sale_total", "profit"}:
            return self._company_basis_total(basis, period)
        row = connection.execute(
            """
            SELECT COALESCE(SUM(amount),0) AS total
            FROM hr_payroll_items
            WHERE payroll_period_id=? AND employee_id=? AND item_type IN ('salary','benefit','commission')
            """,
            (period_id, employee_id),
        ).fetchone()
        return float(row["total"] or 0)

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

    def payroll_period(self, period_id: int) -> dict[str, Any] | None:
        self.init_schema()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM hr_payroll_periods WHERE id=?",
                (period_id,),
            ).fetchone()
        return dict(row) if row else None

    def employee_payment_summary(self, period_id: int, employee_id: int) -> dict[str, Any]:
        self.init_schema()
        employee = self.employee(employee_id)
        period = self.payroll_period(period_id)
        items = [
            item
            for item in self.payroll_items(period_id)
            if int(item["employee_id"]) == int(employee_id)
        ]
        salary_amount = self._sum_items(items, {"salary"})
        benefit_amount = self._sum_items(items, {"benefit"})
        commission_amount = self._sum_items(items, {"commission"})
        discount_amount = self._sum_items(items, {"discount"})
        employer_charge_amount = self._sum_items(items, {"employer_charge"})
        gross_amount = salary_amount + benefit_amount + commission_amount
        contract = str((employee or {}).get("contract_type") or "")
        return {
            "period": period,
            "employee": employee,
            "items": items,
            "document_type": "Folha de pagamento" if contract == "CLT" else "Demonstrativo",
            "salary_amount": salary_amount,
            "benefit_amount": benefit_amount,
            "commission_amount": commission_amount,
            "gross_amount": gross_amount,
            "discount_amount": discount_amount,
            "employer_charge_amount": employer_charge_amount,
            "net_amount": gross_amount - discount_amount,
        }

    def payroll_summaries(
        self,
        period_id: int,
        *,
        contract_type: str | None = None,
    ) -> list[dict[str, Any]]:
        summaries = []
        for employee in self.employees():
            if contract_type and str(employee["contract_type"]) != contract_type:
                continue
            summary = self.employee_payment_summary(period_id, int(employee["id"]))
            if summary["items"]:
                summaries.append(summary)
        return summaries

    def _sum_items(self, items: list[dict[str, Any]], item_types: set[str]) -> float:
        return float(
            sum(float(item["amount"] or 0) for item in items if item["item_type"] in item_types),
        )

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

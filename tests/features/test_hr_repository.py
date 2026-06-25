import sqlite3
from pathlib import Path

from app.features.hr.repository import HRRepository


def _prepare_database(path: Path) -> HRRepository:
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                order_number TEXT,
                total_amount REAL,
                overprice REAL,
                status TEXT,
                created_at TEXT
            )
            """,
        )
        connection.execute(
            """
            INSERT INTO orders(client_id,order_number,total_amount,overprice,status,created_at)
            VALUES(?,?,?,?,?,?)
            """,
            (1, "PED-RH-0001", 10000.0, 2500.0, "Faturado", "2026-06-15"),
        )
        connection.commit()
    repository = HRRepository(path)
    repository.init_schema()
    return repository


def test_employee_is_created_with_base_salary(tmp_path: Path) -> None:
    repository = _prepare_database(tmp_path / "hr.db")

    employee_id = repository.create_employee(
        full_name="Colaborador QA",
        document="123",
        email="qa@example.invalid",
        phone="11999999999",
        department_id=None,
        job_title="Analista",
        contract_type="CLT",
        admission_date="2026-06-01",
        status="Ativo",
        base_salary=3500.0,
        user_id=None,
        manager_user_id=None,
        notes="",
    )

    employee = repository.employee(employee_id)
    assert employee["full_name"] == "Colaborador QA"
    assert employee["base_salary"] == 3500.0


def test_payroll_generates_salary_fixed_benefit_and_sale_commission(
    tmp_path: Path,
) -> None:
    repository = _prepare_database(tmp_path / "hr.db")
    employee_id = repository.create_employee(
        full_name="Vendedor QA",
        document="456",
        email="seller@example.invalid",
        phone="11888888888",
        department_id=None,
        job_title="Vendedor",
        contract_type="CLT",
        admission_date="2026-06-01",
        status="Ativo",
        base_salary=2000.0,
        user_id=None,
        manager_user_id=None,
        notes="",
    )
    repository.create_commission_rule(
        name="Comissão venda total",
        employee_id=employee_id,
        profile_id=None,
        basis="sale_total",
        calculation_scope="company",
        percentage_type="fixed",
        fixed_percentage=5.0,
        is_active=True,
    )
    repository.create_benefit_rule(
        name="Vale alimentação",
        employee_id=employee_id,
        profile_id=None,
        benefit_type="fixed_monthly",
        basis="fixed",
        calculation_scope="individual",
        fixed_amount=600.0,
        percentage=0.0,
        target_value=0.0,
        is_active=True,
    )

    period_id = repository.generate_payroll_period(
        period="2026-06",
        created_by_user_id=1,
    )
    items = repository.payroll_items(period_id)

    assert {item["item_type"] for item in items} == {"salary", "benefit", "commission"}
    assert sum(item["amount"] for item in items) == 3100.0
    assert any(item["description"] == "Comissão venda total" and item["amount"] == 500.0 for item in items)

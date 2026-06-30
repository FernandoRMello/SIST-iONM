import sqlite3
from pathlib import Path

from app.features.hr.repository import HRRepository


def _prepare_database(path: Path) -> HRRepository:
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE sellers (
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


def test_seller_employee_is_synced_with_sellers_catalog(tmp_path: Path) -> None:
    repository = _prepare_database(tmp_path / "hr.db")

    employee_id = repository.create_employee(
        full_name="Representante QA",
        document="789",
        email="representante@example.invalid",
        phone="11777777777",
        department_id=None,
        job_title="Vendedor",
        contract_type="PJ",
        admission_date="2026-06-01",
        status="Ativo",
        base_salary=1200.0,
        user_id=None,
        manager_user_id=None,
        notes="",
        is_seller=True,
        seller_commission_rate=12.5,
    )

    employee = repository.employee(employee_id)

    assert employee["seller_id"] is not None
    with sqlite3.connect(repository.database_path) as connection:
        seller = connection.execute(
            "SELECT name,email,phone,commission_rate,active FROM sellers WHERE id=?",
            (employee["seller_id"],),
        ).fetchone()
    assert seller == ("Representante QA", "representante@example.invalid", "11777777777", 12.5, "Sim")


def test_employee_can_be_updated_and_deleted(tmp_path: Path) -> None:
    repository = _prepare_database(tmp_path / "hr.db")
    employee_id = repository.create_employee(
        full_name="Colaborador Editável",
        document="123",
        email="editavel@example.invalid",
        phone="11999999999",
        department_id=None,
        job_title="Analista",
        contract_type="CLT",
        admission_date="2026-06-01",
        status="Ativo",
        base_salary=2500,
        user_id=None,
        manager_user_id=None,
        notes="Original",
    )

    repository.update_employee(
        employee_id,
        full_name="Colaborador Revisado",
        document="456",
        email="revisado@example.invalid",
        phone="11888888888",
        job_title="Financeiro",
        contract_type="PJ",
        admission_date="2026-06-02",
        status="Inativo",
        base_salary=3200,
        notes="Revisado",
        is_seller=True,
        seller_commission_rate=7.5,
    )

    updated = repository.employee(employee_id)
    assert updated["full_name"] == "Colaborador Revisado"
    assert updated["contract_type"] == "PJ"
    assert updated["base_salary"] == 3200
    assert updated["is_seller"] == "Sim"
    assert updated["seller_id"] is not None

    repository.delete_employee(employee_id)

    assert repository.employee(employee_id) is None


def test_hr_rules_and_payroll_period_can_be_updated_and_deleted(tmp_path: Path) -> None:
    repository = _prepare_database(tmp_path / "hr.db")
    employee_id = repository.create_employee(
        full_name="Regras QA",
        document="123",
        email="regras@example.invalid",
        phone="11999999999",
        department_id=None,
        job_title="Vendedor",
        contract_type="CLT",
        admission_date="2026-06-01",
        status="Ativo",
        base_salary=2000,
        user_id=None,
        manager_user_id=None,
        notes="",
    )
    commission_id = repository.create_commission_rule(
        name="Comissão antiga",
        employee_id=employee_id,
        profile_id=None,
        basis="sale_total",
        calculation_scope="company",
        percentage_type="fixed",
        fixed_percentage=2,
        is_active=True,
    )
    benefit_id = repository.create_benefit_rule(
        name="Benefício antigo",
        employee_id=employee_id,
        profile_id=None,
        benefit_type="fixed_monthly",
        basis="fixed",
        calculation_scope="individual",
        fixed_amount=100,
        percentage=0,
        target_value=0,
        is_active=True,
    )
    adjustment_id = repository.create_payroll_adjustment_rule(
        name="Desconto antigo",
        target_contract="CLT",
        item_type="discount",
        basis="base_salary",
        fixed_amount=0,
        percentage=5,
        is_active=True,
    )

    repository.update_commission_rule(
        commission_id,
        name="Comissão revisada",
        employee_id=None,
        basis="profit",
        calculation_scope="individual",
        fixed_percentage=3.5,
        is_active=False,
    )
    repository.update_benefit_rule(
        benefit_id,
        name="Benefício revisado",
        employee_id=None,
        benefit_type="performance",
        basis="commission",
        calculation_scope="company",
        fixed_amount=0,
        percentage=10,
        target_value=0,
        is_active=False,
    )
    repository.update_payroll_adjustment_rule(
        adjustment_id,
        name="Encargo revisado",
        target_contract="Todos",
        item_type="employer_charge",
        basis="gross_pay",
        fixed_amount=10,
        percentage=1.5,
        is_active=False,
    )

    assert repository.commission_rules()[0]["name"] == "Comissão revisada"
    assert repository.commission_rules()[0]["is_active"] == "Não"
    assert repository.benefit_rules()[0]["basis"] == "commission"
    assert repository.payroll_adjustment_rules()[0]["item_type"] == "employer_charge"

    period_id = repository.generate_payroll_period(period="2026-06", created_by_user_id=1)
    repository.delete_commission_rule(commission_id)
    repository.delete_benefit_rule(benefit_id)
    repository.delete_payroll_adjustment_rule(adjustment_id)
    repository.delete_payroll_period(period_id)

    assert repository.commission_rules() == []
    assert repository.benefit_rules() == []
    assert repository.payroll_adjustment_rules() == []
    assert repository.payroll_period(period_id) is None


def test_clt_payroll_generates_discounts_charges_and_net_summary(
    tmp_path: Path,
) -> None:
    repository = _prepare_database(tmp_path / "hr.db")
    employee_id = repository.create_employee(
        full_name="CLT QA",
        document="111",
        email="clt@example.invalid",
        phone="11666666666",
        department_id=None,
        job_title="Analista",
        contract_type="CLT",
        admission_date="2026-06-01",
        status="Ativo",
        base_salary=3000.0,
        user_id=None,
        manager_user_id=None,
        notes="",
    )
    repository.create_payroll_adjustment_rule(
        name="INSS QA",
        target_contract="CLT",
        item_type="discount",
        basis="base_salary",
        fixed_amount=0,
        percentage=10,
        is_active=True,
    )
    repository.create_payroll_adjustment_rule(
        name="FGTS QA",
        target_contract="CLT",
        item_type="employer_charge",
        basis="base_salary",
        fixed_amount=0,
        percentage=8,
        is_active=True,
    )

    period_id = repository.generate_payroll_period(period="2026-06", created_by_user_id=1)
    summary = repository.employee_payment_summary(period_id, employee_id)

    assert summary["gross_amount"] == 3000.0
    assert summary["discount_amount"] == 300.0
    assert summary["employer_charge_amount"] == 240.0
    assert summary["net_amount"] == 2700.0


def test_commissioned_statement_separates_commission_benefit_and_basis(
    tmp_path: Path,
) -> None:
    repository = _prepare_database(tmp_path / "hr.db")
    employee_id = repository.create_employee(
        full_name="Comissionado QA",
        document="222",
        email="comissionado@example.invalid",
        phone="11555555555",
        department_id=None,
        job_title="Representante",
        contract_type="Representante",
        admission_date="2026-06-01",
        status="Ativo",
        base_salary=0,
        user_id=None,
        manager_user_id=None,
        notes="",
        is_seller=True,
        seller_commission_rate=5,
    )
    repository.create_commission_rule(
        name="Comissão representante",
        employee_id=employee_id,
        profile_id=None,
        basis="profit",
        calculation_scope="company",
        percentage_type="fixed",
        fixed_percentage=10,
        is_active=True,
    )
    repository.create_benefit_rule(
        name="Ajuda de custo",
        employee_id=employee_id,
        profile_id=None,
        benefit_type="fixed_monthly",
        basis="fixed",
        calculation_scope="individual",
        fixed_amount=150,
        percentage=0,
        target_value=0,
        is_active=True,
    )

    period_id = repository.generate_payroll_period(period="2026-06", created_by_user_id=1)
    statement = repository.employee_payment_summary(period_id, employee_id)

    assert statement["document_type"] == "Demonstrativo"
    assert statement["commission_amount"] == 250.0
    assert statement["benefit_amount"] == 150.0
    assert statement["net_amount"] == 400.0
    assert any(item["basis_amount"] == 2500.0 for item in statement["items"])


def test_payroll_uses_legacy_orders_items_for_seller_commission_and_benefit(
    tmp_path: Path,
) -> None:
    path = tmp_path / "legacy-hr.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE sellers (
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
        seller_id = connection.execute(
            "INSERT INTO sellers(name,email,commission_rate,active) VALUES(?,?,?,?)",
            ("Alan QA", "alan@example.invalid", 10, "Sim"),
        ).lastrowid
        other_seller_id = connection.execute(
            "INSERT INTO sellers(name,email,commission_rate,active) VALUES(?,?,?,?)",
            ("Outro QA", "outro@example.invalid", 10, "Sim"),
        ).lastrowid
        connection.execute("CREATE TABLE opportunities (id INTEGER PRIMARY KEY, seller_id INTEGER, status TEXT)")
        connection.execute(
            """
            CREATE TABLE opportunity_items (
                id INTEGER PRIMARY KEY,
                opportunity_id INTEGER,
                quantity REAL,
                supplier_unit_price REAL,
                sale_unit_price REAL,
                seller_commission_rate REAL
            )
            """,
        )
        connection.execute(
            """
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                opportunity_id INTEGER,
                order_number TEXT,
                created_at TEXT,
                status TEXT
            )
            """,
        )
        connection.execute(
            "INSERT INTO opportunities(id,seller_id,status) VALUES(?,?,?)",
            (1, seller_id, "Ganho"),
        )
        connection.execute(
            "INSERT INTO opportunities(id,seller_id,status) VALUES(?,?,?)",
            (2, other_seller_id, "Ganho"),
        )
        connection.execute(
            """
            INSERT INTO opportunity_items(opportunity_id,quantity,supplier_unit_price,sale_unit_price,seller_commission_rate)
            VALUES(?,?,?,?,?)
            """,
            (1, 2, 1000, 1500, 10),
        )
        connection.execute(
            """
            INSERT INTO opportunity_items(opportunity_id,quantity,supplier_unit_price,sale_unit_price,seller_commission_rate)
            VALUES(?,?,?,?,?)
            """,
            (2, 1, 1000, 3000, 10),
        )
        connection.execute(
            "INSERT INTO orders(opportunity_id,order_number,created_at,status) VALUES(?,?,?,?)",
            (1, "PED-ALAN", "2026-06-20", "Faturado"),
        )
        connection.execute(
            "INSERT INTO orders(opportunity_id,order_number,created_at,status) VALUES(?,?,?,?)",
            (2, "PED-OUTRO", "2026-06-20", "Faturado"),
        )
        connection.commit()

    repository = HRRepository(path)
    repository.init_schema()
    employee_id = repository.create_employee(
        full_name="Alan QA",
        document="333",
        email="alan@example.invalid",
        phone="11444444444",
        department_id=None,
        job_title="Vendedor",
        contract_type="PJ",
        admission_date="2026-06-01",
        status="Ativo",
        base_salary=0,
        user_id=None,
        manager_user_id=None,
        notes="",
        is_seller=True,
        seller_commission_rate=10,
    )
    repository.create_commission_rule(
        name="Comissão individual por lucro",
        employee_id=employee_id,
        profile_id=None,
        basis="profit",
        calculation_scope="individual",
        percentage_type="fixed",
        fixed_percentage=10,
        is_active=True,
    )
    repository.create_benefit_rule(
        name="Benefício sobre comissão",
        employee_id=employee_id,
        profile_id=None,
        benefit_type="performance",
        basis="commission",
        calculation_scope="individual",
        fixed_amount=0,
        percentage=20,
        target_value=0,
        is_active=True,
    )

    period_id = repository.generate_payroll_period(period="2026-06", created_by_user_id=1)
    statement = repository.employee_payment_summary(period_id, employee_id)

    assert statement["commission_amount"] == 100.0
    assert statement["benefit_amount"] == 20.0
    assert statement["net_amount"] == 120.0

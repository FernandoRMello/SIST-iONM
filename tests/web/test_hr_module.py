import sqlite3

from fastapi.testclient import TestClient

from tests.conftest import LegacyTestState


def test_hr_pages_require_permission(
    authenticated_client: TestClient,
    admin_client: TestClient,
) -> None:
    denied = authenticated_client.get("/hr/employees")
    allowed = admin_client.get("/hr/employees")

    assert denied.status_code == 403
    assert allowed.status_code == 200
    assert "Colaboradores" in allowed.text


def test_admin_can_create_employee_and_link_user(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    response = admin_client.post(
        "/hr/employees",
        data={
            "full_name": "Colaborador Web QA",
            "document": "123",
            "email": "colaborador.web@example.invalid",
            "phone": "11999990000",
            "job_title": "Analista",
            "contract_type": "CLT",
            "admission_date": "2026-06-01",
            "status": "Ativo",
            "base_salary": "3000",
            "notes": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        connection.row_factory = sqlite3.Row
        employee = connection.execute(
            "SELECT * FROM hr_employees WHERE full_name=?",
            ("Colaborador Web QA",),
        ).fetchone()

    linked = admin_client.post(
        f"/hr/employees/{employee['id']}/create-user",
        data={"username": "colaborador.web", "password": "Senha@123", "profile_id": ""},
        follow_redirects=False,
    )

    assert linked.status_code == 303
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        user = connection.execute(
            "SELECT id FROM users WHERE username=?",
            ("colaborador.web",),
        ).fetchone()
        linked_user_id = connection.execute(
            "SELECT user_id FROM hr_employees WHERE id=?",
            (employee["id"],),
        ).fetchone()[0]
    assert user is not None
    assert linked_user_id == user[0]


def test_admin_can_create_hr_rules_and_generate_payroll(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    admin_client.post(
        "/hr/employees",
        data={
            "full_name": "Folha Web QA",
            "document": "456",
            "email": "folha.web@example.invalid",
            "phone": "11888880000",
            "job_title": "Vendedor",
            "contract_type": "CLT",
            "admission_date": "2026-06-01",
            "status": "Ativo",
            "base_salary": "2000",
            "notes": "",
        },
    )
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        employee_id = connection.execute(
            "SELECT id FROM hr_employees WHERE full_name=?",
            ("Folha Web QA",),
        ).fetchone()[0]

    commission = admin_client.post(
        "/hr/commission-rules",
        data={
            "name": "Comissão geral QA",
            "employee_id": str(employee_id),
            "basis": "sale_total",
            "calculation_scope": "company",
            "fixed_percentage": "1",
            "is_active": "Sim",
        },
        follow_redirects=False,
    )
    benefit = admin_client.post(
        "/hr/benefit-rules",
        data={
            "name": "Benefício fixo QA",
            "employee_id": str(employee_id),
            "benefit_type": "fixed_monthly",
            "basis": "fixed",
            "calculation_scope": "individual",
            "fixed_amount": "300",
            "percentage": "0",
            "target_value": "0",
            "is_active": "Sim",
        },
        follow_redirects=False,
    )
    payroll = admin_client.post(
        "/hr/payroll/generate",
        data={"period": "2026-06"},
        follow_redirects=False,
    )

    assert commission.status_code == 303
    assert benefit.status_code == 303
    assert payroll.status_code == 303
    page = admin_client.get("/hr/payroll")
    assert "2026-06" in page.text
    assert "Folha Web QA" in page.text

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


def test_hr_employee_form_uses_list_fields_for_known_domains(
    admin_client: TestClient,
) -> None:
    response = admin_client.get("/hr/employees")

    assert response.status_code == 200
    assert 'id="employee-job"' in response.text
    assert 'name="job_title"' in response.text
    assert '<select class="ui-field__control" id="employee-job" name="job_title"' in response.text
    assert "Vendedor" in response.text
    assert "Representante" in response.text
    assert '<select class="ui-field__control" id="employee-contract" name="contract_type"' in response.text


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


def test_seller_employee_creates_seller_and_user_link(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    response = admin_client.post(
        "/hr/employees",
        data={
            "full_name": "Representante Web QA",
            "document": "789",
            "email": "representante.web@example.invalid",
            "phone": "11777770000",
            "job_title": "Vendedor",
            "contract_type": "PJ",
            "admission_date": "2026-06-01",
            "status": "Ativo",
            "base_salary": "1200",
            "is_seller": "Sim",
            "seller_commission_rate": "12,5",
            "notes": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        connection.row_factory = sqlite3.Row
        employee = connection.execute(
            "SELECT * FROM hr_employees WHERE full_name=?",
            ("Representante Web QA",),
        ).fetchone()
        seller = connection.execute(
            "SELECT commission_rate FROM sellers WHERE id=?",
            (employee["seller_id"],),
        ).fetchone()

    linked = admin_client.post(
        f"/hr/employees/{employee['id']}/create-user",
        data={"username": "representante.web", "password": "Senha@123", "profile_id": ""},
        follow_redirects=False,
    )

    assert employee["seller_id"] is not None
    assert seller[0] == 12.5
    assert linked.status_code == 303
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        user = connection.execute(
            "SELECT seller_id FROM users WHERE username=?",
            ("representante.web",),
        ).fetchone()
    assert user[0] == employee["seller_id"]


def test_hr_employee_page_exposes_edit_and_delete_actions(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    admin_client.post(
        "/hr/employees",
        data={
            "full_name": "Colaborador Ações QA",
            "document": "123",
            "email": "acoes@example.invalid",
            "phone": "11999990000",
            "job_title": "Analista",
            "contract_type": "CLT",
            "admission_date": "2026-06-01",
            "status": "Ativo",
            "base_salary": "3000",
            "notes": "",
        },
    )
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        employee_id = connection.execute(
            "SELECT id FROM hr_employees WHERE full_name=?",
            ("Colaborador Ações QA",),
        ).fetchone()[0]

    page = admin_client.get("/hr/employees")

    assert page.status_code == 200
    assert f'action="/hr/employees/{employee_id}/update"' in page.text
    assert f'action="/hr/employees/{employee_id}/delete"' in page.text
    assert "Salvar alterações" in page.text
    assert "Apagar" in page.text


def test_admin_can_update_and_delete_employee_from_web(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    admin_client.post(
        "/hr/employees",
        data={
            "full_name": "Colaborador Web Editar QA",
            "document": "123",
            "email": "editar@example.invalid",
            "phone": "11999990000",
            "job_title": "Analista",
            "contract_type": "CLT",
            "admission_date": "2026-06-01",
            "status": "Ativo",
            "base_salary": "3000",
            "notes": "",
        },
    )
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        employee_id = connection.execute(
            "SELECT id FROM hr_employees WHERE full_name=?",
            ("Colaborador Web Editar QA",),
        ).fetchone()[0]

    updated = admin_client.post(
        f"/hr/employees/{employee_id}/update",
        data={
            "full_name": "Colaborador Web Editado QA",
            "document": "456",
            "email": "editado@example.invalid",
            "phone": "11888880000",
            "job_title": "Financeiro",
            "contract_type": "PJ",
            "admission_date": "2026-06-02",
            "status": "Inativo",
            "base_salary": "4500",
            "is_seller": "Sim",
            "seller_commission_rate": "7,5",
            "notes": "Atualizado",
        },
        follow_redirects=False,
    )

    assert updated.status_code == 303
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        connection.row_factory = sqlite3.Row
        employee = connection.execute(
            "SELECT * FROM hr_employees WHERE id=?",
            (employee_id,),
        ).fetchone()
    assert employee["full_name"] == "Colaborador Web Editado QA"
    assert employee["seller_id"] is not None

    deleted = admin_client.post(
        f"/hr/employees/{employee_id}/delete",
        follow_redirects=False,
    )

    assert deleted.status_code == 303
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        missing = connection.execute(
            "SELECT id FROM hr_employees WHERE id=?",
            (employee_id,),
        ).fetchone()
    assert missing is None


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
    page = admin_client.get("/hr/payroll?period=2026-06")
    assert "2026-06" in page.text
    assert "Folha Web QA" in page.text


def test_hr_rules_and_payroll_pages_expose_edit_and_delete_actions(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    admin_client.post(
        "/hr/employees",
        data={
            "full_name": "Regras Web Ações QA",
            "document": "456",
            "email": "regras.acoes@example.invalid",
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
            ("Regras Web Ações QA",),
        ).fetchone()[0]
    admin_client.post(
        "/hr/commission-rules",
        data={
            "name": "Comissão Ações QA",
            "employee_id": str(employee_id),
            "basis": "sale_total",
            "calculation_scope": "company",
            "fixed_percentage": "1",
            "is_active": "Sim",
        },
    )
    admin_client.post(
        "/hr/benefit-rules",
        data={
            "name": "Benefício Ações QA",
            "employee_id": str(employee_id),
            "benefit_type": "fixed_monthly",
            "basis": "fixed",
            "calculation_scope": "individual",
            "fixed_amount": "300",
            "percentage": "0",
            "target_value": "0",
            "is_active": "Sim",
        },
    )
    admin_client.post(
        "/hr/payroll-adjustment-rules",
        data={
            "name": "Desconto Ações QA",
            "target_contract": "CLT",
            "item_type": "discount",
            "basis": "base_salary",
            "fixed_amount": "0",
            "percentage": "5",
            "is_active": "Sim",
        },
    )
    admin_client.post("/hr/payroll/generate", data={"period": "2026-06"})
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        commission_id = connection.execute("SELECT id FROM hr_commission_rules").fetchone()[0]
        benefit_id = connection.execute("SELECT id FROM hr_benefit_rules").fetchone()[0]
        adjustment_id = connection.execute("SELECT id FROM hr_payroll_adjustment_rules").fetchone()[0]
        period_id = connection.execute("SELECT id FROM hr_payroll_periods WHERE period='2026-06'").fetchone()[0]

    rules_page = admin_client.get("/hr/rules")
    payroll_page = admin_client.get("/hr/payroll?period=2026-06")

    assert f'action="/hr/commission-rules/{commission_id}/update"' in rules_page.text
    assert f'action="/hr/commission-rules/{commission_id}/delete"' in rules_page.text
    assert f'action="/hr/benefit-rules/{benefit_id}/update"' in rules_page.text
    assert f'action="/hr/benefit-rules/{benefit_id}/delete"' in rules_page.text
    assert f'action="/hr/payroll-adjustment-rules/{adjustment_id}/update"' in rules_page.text
    assert f'action="/hr/payroll-adjustment-rules/{adjustment_id}/delete"' in rules_page.text
    assert f'action="/hr/payroll/{period_id}/reopen"' in payroll_page.text
    assert f'action="/hr/payroll/{period_id}/delete"' in payroll_page.text


def test_payroll_print_and_commission_statement_pages(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    admin_client.post(
        "/hr/employees",
        data={
            "full_name": "CLT Impressão QA",
            "document": "111",
            "email": "clt.impressao@example.invalid",
            "phone": "11666660000",
            "job_title": "Analista",
            "contract_type": "CLT",
            "admission_date": "2026-06-01",
            "status": "Ativo",
            "base_salary": "3000",
            "notes": "",
        },
    )
    admin_client.post(
        "/hr/employees",
        data={
            "full_name": "Comissionado Impressão QA",
            "document": "222",
            "email": "comissionado.impressao@example.invalid",
            "phone": "11555550000",
            "job_title": "Representante",
            "contract_type": "Representante",
            "admission_date": "2026-06-01",
            "status": "Ativo",
            "base_salary": "0",
            "is_seller": "Sim",
            "seller_commission_rate": "5",
            "notes": "",
        },
    )
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        clt_id = connection.execute(
            "SELECT id FROM hr_employees WHERE full_name=?",
            ("CLT Impressão QA",),
        ).fetchone()[0]
        commissioned_id = connection.execute(
            "SELECT id FROM hr_employees WHERE full_name=?",
            ("Comissionado Impressão QA",),
        ).fetchone()[0]

    admin_client.post(
        "/hr/payroll-adjustment-rules",
        data={
            "name": "INSS QA",
            "target_contract": "CLT",
            "item_type": "discount",
            "basis": "base_salary",
            "fixed_amount": "0",
            "percentage": "10",
            "is_active": "Sim",
        },
    )
    admin_client.post(
        "/hr/payroll-adjustment-rules",
        data={
            "name": "FGTS QA",
            "target_contract": "CLT",
            "item_type": "employer_charge",
            "basis": "base_salary",
            "fixed_amount": "0",
            "percentage": "8",
            "is_active": "Sim",
        },
    )
    admin_client.post(
        "/hr/commission-rules",
        data={
            "name": "Comissão demonstrativo QA",
            "employee_id": str(commissioned_id),
            "basis": "profit",
            "calculation_scope": "company",
            "fixed_percentage": "10",
            "is_active": "Sim",
        },
    )
    admin_client.post(
        "/hr/benefit-rules",
        data={
            "name": "Ajuda de custo QA",
            "employee_id": str(commissioned_id),
            "benefit_type": "fixed_monthly",
            "basis": "fixed",
            "calculation_scope": "individual",
            "fixed_amount": "150",
            "percentage": "0",
            "target_value": "0",
            "is_active": "Sim",
        },
    )
    admin_client.post("/hr/payroll/generate", data={"period": "2026-06"})
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        period_id = connection.execute(
            "SELECT id FROM hr_payroll_periods WHERE period=?",
            ("2026-06",),
        ).fetchone()[0]

    print_page = admin_client.get(f"/hr/payroll/{period_id}/print-clt")
    statement_page = admin_client.get(f"/hr/payroll/{period_id}/statements")
    individual_page = admin_client.get(
        f"/hr/payroll/{period_id}/employees/{clt_id}/statement",
    )

    assert print_page.status_code == 200
    assert "Folha de pagamento CLT" in print_page.text
    assert "INSS QA" in print_page.text
    assert "FGTS QA" in print_page.text
    assert "Valor líquido" in print_page.text
    assert statement_page.status_code == 200
    assert "Demonstrativo de pagamento" in statement_page.text
    assert "Comissionado Impressão QA" in statement_page.text
    assert "Base de cálculo" in statement_page.text
    assert "Benefício" in statement_page.text
    assert individual_page.status_code == 200

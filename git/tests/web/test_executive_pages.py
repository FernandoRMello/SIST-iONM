import re
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from tests.conftest import LegacyTestState

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = REPO_ROOT / "app" / "templates"
ERROR_TEMPLATES = REPO_ROOT / "app" / "shared" / "web" / "templates" / "errors"


def _money_br(value: float) -> str:
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def test_dashboard_uses_executive_components(admin_client: TestClient) -> None:
    response = admin_client.get("/")

    assert response.status_code == 200
    assert response.text.count('data-component="stat-card"') == 6
    assert response.text.count('href="/opportunities"') >= 1
    assert 'data-action="toggle-money"' in response.text
    assert "Probabilidade" in response.text
    assert "%" in response.text


def test_bi_has_explicit_executive_sections_and_no_inline_handlers(
    admin_client: TestClient,
) -> None:
    response = admin_client.get("/bi-gerencial")

    assert response.status_code == 200
    for heading in (
        "Visão executiva",
        "Cenários de investimento",
        "Recomendações comerciais",
        "Pipeline por oportunidade",
    ):
        assert heading in response.text
    assert not re.search(r"\son(?:click|change|submit)=", response.text, re.IGNORECASE)


def test_dashboard_and_bi_include_overdue_payables(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        connection.execute(
            """
            INSERT INTO payables(description,category,amount,due_date,status,notes)
            VALUES(?,?,?,?,?,?)
            """,
            (
                "Conta vencida BI QA",
                "Fornecedor",
                1234,
                "2026-06-10",
                "Vencido",
                "Obrigação vencida deve entrar na visão gerencial",
            ),
        )
        expected_total = connection.execute(
            """
            SELECT
                (SELECT COALESCE(SUM(amount),0)
                 FROM payables
                 WHERE status IN ('Aberto','Vencido','Inadimplente','Agendado'))
                +
                (SELECT COALESCE(SUM(
                    CASE
                      WHEN item.item_type='discount' THEN -COALESCE(item.amount,0)
                      ELSE COALESCE(item.amount,0)
                    END
                 ),0)
                 FROM hr_payroll_items item
                 JOIN hr_payroll_periods period ON period.id=item.payroll_period_id
                 WHERE COALESCE(period.status,'Rascunho') <> 'Paga'
                   AND item.item_type IN ('salary','benefit','commission','discount','employer_charge'))
                AS total
            """,
        ).fetchone()[0]
        connection.commit()

    dashboard = admin_client.get("/")
    bi = admin_client.get("/bi-gerencial")

    assert dashboard.status_code == 200
    assert _money_br(expected_total) in dashboard.text
    assert bi.status_code == 200
    assert _money_br(expected_total) in bi.text
    assert "Compromissos a pagar" in bi.text
    assert "Conta vencida BI QA" in bi.text


def test_dashboard_and_bi_include_unpaid_payroll_and_benefits(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    with sqlite3.connect(legacy_test_state.database_path) as connection:
        now = "2026-06-26T10:00:00"
        employee_id = connection.execute(
            """
            INSERT INTO hr_employees(
                full_name, contract_type, status, base_salary, created_at, updated_at
            )
            VALUES(?,?,?,?,?,?)
            """,
            ("Folha BI QA", "CLT", "Ativo", 0, now, now),
        ).lastrowid
        period_id = connection.execute(
            """
            INSERT INTO hr_payroll_periods(period,status,created_by_user_id,created_at)
            VALUES(?,?,?,?)
            """,
            ("2026-08", "Aprovada", 1, now),
        ).lastrowid
        for item_type, description, amount in (
            ("salary", "Salário Folha BI QA", 400),
            ("benefit", "Benefício Folha BI QA", 100),
            ("discount", "Desconto Folha BI QA", 50),
            ("employer_charge", "Encargo Folha BI QA", 80),
        ):
            connection.execute(
                """
                INSERT INTO hr_payroll_items(
                    payroll_period_id, employee_id, item_type, description,
                    basis_amount, percentage, amount, source_type, source_id, created_at
                )
                VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                (period_id, employee_id, item_type, description, 0, 0, amount, "qa", 1, now),
            )
        expected_total = connection.execute(
            """
            SELECT
                (SELECT COALESCE(SUM(amount),0)
                 FROM payables
                 WHERE status IN ('Aberto','Vencido','Inadimplente','Agendado'))
                +
                (SELECT COALESCE(SUM(
                    CASE
                      WHEN item.item_type='discount' THEN -COALESCE(item.amount,0)
                      ELSE COALESCE(item.amount,0)
                    END
                 ),0)
                 FROM hr_payroll_items item
                 JOIN hr_payroll_periods period ON period.id=item.payroll_period_id
                 WHERE COALESCE(period.status,'Rascunho') <> 'Paga'
                   AND item.item_type IN ('salary','benefit','commission','discount','employer_charge'))
                AS total
            """,
        ).fetchone()[0]
        connection.commit()

    dashboard = admin_client.get("/")
    bi = admin_client.get("/bi-gerencial")

    assert dashboard.status_code == 200
    assert _money_br(expected_total) in dashboard.text
    assert bi.status_code == 200
    assert _money_br(expected_total) in bi.text
    assert "Folha 2026-08 · Folha BI QA" in bi.text


def test_login_is_labelled_local_and_password_toggle_is_accessible(
    legacy_client: TestClient,
) -> None:
    response = legacy_client.get("/login")

    assert response.status_code == 200
    assert '<label' in response.text
    assert 'for="username"' in response.text
    assert 'for="password"' in response.text
    assert 'autocomplete="username"' in response.text
    assert 'autocomplete="current-password"' in response.text
    assert 'data-action="toggle-password"' in response.text
    assert not re.search(r'(?:src|href)="https?://', response.text)


def test_error_templates_are_safe_and_support_correlation_id() -> None:
    expected = {"400.html", "403.html", "404.html", "500.html"}
    assert {path.name for path in ERROR_TEMPLATES.glob("*.html")} >= expected

    for filename in expected:
        source = (ERROR_TEMPLATES / filename).read_text(encoding="utf-8")
        assert "correlation_id" in source
        assert 'href="/"' in source
        assert "exception" not in source

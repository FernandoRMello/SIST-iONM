import re
from pathlib import Path

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = REPO_ROOT / "app" / "templates"


def test_finance_templates_use_shared_accessible_contracts() -> None:
    sources = {
        name: (TEMPLATES / name).read_text(encoding="utf-8")
        for name in ("finance.html", "commissions.html", "seller_reports.html")
    }

    for name, source in sources.items():
        assert "page_header" in source, name
        assert "/assets/css/finance.css" in source, name
        assert not re.search(r"\son(?:click|change|submit|input)=", source, re.IGNORECASE), name

    finance = sources["finance.html"]
    for segment in ("receivables", "payables", "costs"):
        assert f"segment={segment}" in finance
    assert "aria-current" in finance
    assert finance.count('action="/finance/costs/add"') == 1
    for label in ("Total a receber", "Total a pagar", "Total de custos"):
        assert label in finance
    assert "empty_state" in finance

    commissions = sources["commissions.html"]
    assert "data-table-search" in commissions
    assert "Status:" in commissions
    assert "empty_state" in commissions

    reports = sources["seller_reports.html"]
    for snippet in (
        'data-action="print"',
        'data-action="toggle-money"',
        "ui-report-filters",
        "Resumo da equipe",
        "Avaliação qualitativa",
        "Relatório quantitativo e qualitativo",
    ):
        assert snippet in reports


def test_finance_route_renders_only_selected_segment(admin_client: TestClient) -> None:
    expectations = {
        "/finance": ("receivables", "Contas a receber", "Overprice pedido PED-QA-0001"),
        "/finance?segment=payables": ("payables", "Contas a pagar", "Comissão pedido PED-QA-0001"),
        "/finance?segment=costs": ("costs", "Custos", "Frete seed QA"),
    }

    for path, (segment, heading, row_text) in expectations.items():
        response = admin_client.get(path)
        assert response.status_code == 200
        assert f'data-finance-panel="{segment}"' in response.text
        assert heading in response.text
        assert row_text in response.text

    invalid = admin_client.get("/finance?segment=invalid")
    assert invalid.status_code == 200
    assert 'data-finance-panel="receivables"' in invalid.text


def test_commissions_and_reports_render_professional_sections(
    admin_client: TestClient,
) -> None:
    commissions = admin_client.get("/commissions")
    reports = admin_client.get("/reports/sellers")

    assert commissions.status_code == 200
    assert "Comissões por vendedor" in commissions.text
    assert "Vendedor QA Render" in commissions.text
    assert reports.status_code == 200
    assert "Resumo da equipe" in reports.text
    assert "Vendedor QA Render" in reports.text


def test_financial_forms_preserve_backend_field_names() -> None:
    finance = (TEMPLATES / "finance.html").read_text(encoding="utf-8")
    reports = (TEMPLATES / "seller_reports.html").read_text(encoding="utf-8")

    for field_name in (
        "order_id",
        "description",
        "category",
        "cost_center",
        "amount",
        "date",
        "vendor",
        "document",
        "billable",
        "notes",
    ):
        assert f'name="{field_name}"' in finance

    for field_name in (
        "seller_id",
        "period",
        "organization_score",
        "followup_score",
        "opportunity_quality_score",
        "margin_score",
        "predictability_score",
        "strengths",
        "improvements",
        "notes",
    ):
        assert f'name="{field_name}"' in reports

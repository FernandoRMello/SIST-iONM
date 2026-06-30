import re
from pathlib import Path

from fastapi.testclient import TestClient

from tests.conftest import LegacyTestState

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = REPO_ROOT / "app" / "templates"


def test_crm_templates_use_accessible_operational_contracts() -> None:
    sources = {
        name: (TEMPLATES / name).read_text(encoding="utf-8")
        for name in (
            "opportunities.html",
            "opportunity_card.html",
            "orders.html",
            "purchases.html",
        )
    }

    for name, source in sources.items():
        assert "page_header" in source, name
        assert not re.search(r"\son(?:click|change|submit|input)=", source, re.IGNORECASE), name
        assert "/assets/css/crm.css" in source, name

    opportunities = sources["opportunities.html"]
    assert "aria-current" in opportunities
    assert "Probabilidade" in opportunities
    assert "Próximo follow-up" in opportunities
    assert 'aria-label="Mover' in opportunities
    assert "data-disclosure" in opportunities

    card = sources["opportunity_card.html"]
    for field_name in (
        "product_id",
        "quantity",
        "sale_unit_price",
        "seller_commission_rate",
        "content",
        "title",
        "doc_type",
        "file",
    ):
        assert f'name="{field_name}"' in card
    headings = [
        "Sobre o negócio",
        "Produtos do card",
        "Comunicação",
        "Documentos do card",
        "Histórico e anotações",
    ]
    assert [card.index(heading) for heading in headings] == sorted(
        card.index(heading) for heading in headings
    )

    orders = sources["orders.html"]
    assert "Status fiscal" in orders
    assert "Status financeiro" in orders
    assert 'data-action="print"' in orders
    assert 'data-action="toggle-money"' in orders

    purchases = sources["purchases.html"]
    assert "data-table" in purchases
    assert "empty_state" in purchases


def test_crm_surfaces_render_and_preserve_view_state(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
) -> None:
    paths = {
        "/opportunities?view_mode=kanban": ("Pipeline / Registro de Oportunidade", "Kanban"),
        "/opportunities?view_mode=list": ("Lista de oportunidades", "RO-QA-0001"),
        f"/opportunities/{legacy_test_state.ids['opportunity_id']}/card": (
            "Sobre o negócio",
            "Produtos do card",
        ),
        "/orders": ("Pedidos / Fechamento", "Salvar fechamento"),
        "/backoffice/purchases": ("Nova compra", "Cadastrar compra"),
    }

    for path, snippets in paths.items():
        response = admin_client.get(path)
        assert response.status_code == 200, path
        assert '<main class="ui-content"' in response.text
        for snippet in snippets:
            assert snippet in response.text, (path, snippet)

    list_response = admin_client.get("/opportunities?view_mode=list")
    assert 'href="/opportunities?view_mode=list" aria-current="page"' in list_response.text


def test_operational_forms_preserve_backend_field_names() -> None:
    orders = (TEMPLATES / "orders.html").read_text(encoding="utf-8")
    purchases = (TEMPLATES / "purchases.html").read_text(encoding="utf-8")

    for field_name in (
        "supplier_invoice",
        "ionm_invoice",
        "supplier_invoice_date",
        "ionm_invoice_date",
        "expected_receipt_date",
        "receipt_date",
        "fiscal_status",
        "financial_status",
        "received_amount",
        "notes",
    ):
        assert f'name="{field_name}"' in orders

    for field_name in (
        "supplier_id",
        "description",
        "amount",
        "status",
        "issue_date",
        "due_date",
        "notes",
    ):
        assert f'name="{field_name}"' in purchases

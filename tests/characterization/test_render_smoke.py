from collections.abc import Iterable

import pytest
from fastapi.testclient import TestClient

from tests.conftest import LegacyTestState


def assert_page_identity(response_text: str, snippets: Iterable[str]) -> None:
    for snippet in snippets:
        assert snippet in response_text


def test_login_page_renders_with_named_credentials_fields(legacy_client: TestClient) -> None:
    response = legacy_client.get("/login")

    assert response.status_code == 200
    assert_page_identity(response.text, ['name="username"', 'name="password"', "OverpriceON"])


def test_invalid_login_re_renders_login_with_error_message(legacy_client: TestClient) -> None:
    response = legacy_client.post(
        "/login",
        data={"username": "unknown-user", "password": "wrong-password"},
    )

    assert response.status_code == 200
    assert_page_identity(
        response.text,
        ["Usuário ou senha inválidos.", 'name="username"', 'name="password"'],
    )


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/feed",
        "/chat",
        "/profile",
        "/orgchart",
        "/opportunities",
        "/orders",
        "/finance",
        "/settings",
    ],
)
def test_protected_pages_redirect_anonymous_users_to_login(
    legacy_client: TestClient,
    path: str,
) -> None:
    response = legacy_client.get(path, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


@pytest.mark.parametrize(
    ("path_template", "snippets"),
    [
        ("/", ("Painel comercial", "Oportunidades recentes")),
        ("/feed", ("Feed da equipe", "Publicar")),
        ("/chat", ("Conversas", "Chat em tempo real")),
        ("/profile", ("Perfil do usuário", "Atualizar foto")),
        ("/orgchart", ("Organograma", "Pessoas")),
        ("/admin/permissions", ("Administração de perfis", "Salvar permissões")),
        ("/backoffice/purchases", ("Nova compra", "Cadastrar compra")),
        ("/reports/sellers", ("Avaliação qualitativa", "Relatório quantitativo e qualitativo")),
        ("/bi-gerencial", ("BI Gerencial OverpriceON", "Produtos para focar")),
        ("/cadastros/clients", ("Novo Clientes", "Lista")),
        ("/cadastros/clients/edit/{client_id}", ("Editar Clientes", "Cliente QA Render")),
        ("/cadastros/suppliers", ("Novo Fornecedores", "Lista")),
        ("/cadastros/suppliers/edit/{supplier_id}", ("Editar Fornecedores", "Fornecedor QA Render")),
        ("/cadastros/products", ("Novo Produtos", "Lista")),
        ("/cadastros/products/edit/{product_id}", ("Editar Produtos", "Produto QA Render")),
        ("/cadastros/sellers", ("Novo Vendedores", "Lista")),
        ("/cadastros/sellers/edit/{seller_id}", ("Editar Vendedores", "Vendedor QA Render")),
        ("/opportunities?view_mode=kanban", ("Pipeline / Registro de Oportunidade", "Nova oportunidade")),
        ("/opportunities?view_mode=list", ("Lista de oportunidades", "RO-QA-0001")),
        ("/opportunities/{opportunity_id}/card", ("Sobre o negócio", "Produtos do card", "RO-QA-0001")),
        ("/orders", ("Pedidos / Fechamento", "PED-QA-0001", "Salvar fechamento")),
        ("/commissions", ("Comissões por vendedor", "Vendedor QA Render")),
        ("/finance", ("Contas a receber", "Total a receber")),
        ("/finance?segment=payables", ("Contas a pagar", "Total a pagar")),
        ("/finance?segment=costs", ("Novo custo", "Total de custos")),
        ("/settings", ("Empresa e impressão no servidor", "Criar usuário")),
        ("/settings/users/edit/{settings_user_id}", ("Editar usuário", "qa.seller")),
    ],
)
def test_render_routes_cover_all_characterized_templates_and_variants(
    admin_client: TestClient,
    legacy_test_state: LegacyTestState,
    path_template: str,
    snippets: tuple[str, ...],
) -> None:
    response = admin_client.get(path_template.format(**legacy_test_state.ids))

    assert response.status_code == 200
    assert_page_identity(response.text, snippets)

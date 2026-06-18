import re
from pathlib import Path

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = REPO_ROOT / "app" / "templates"
ERROR_TEMPLATES = REPO_ROOT / "app" / "shared" / "web" / "templates" / "errors"


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

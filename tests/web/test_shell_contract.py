import re
from pathlib import Path

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
SHARED_LAYOUT = REPO_ROOT / "app" / "shared" / "web" / "templates" / "layouts" / "base.html"
COMPATIBILITY_LAYOUT = REPO_ROOT / "app" / "templates" / "base.html"
SHELL_SCRIPT = REPO_ROOT / "app" / "shared" / "web" / "static" / "js" / "app-shell.js"
NAVIGATION_SCRIPT = REPO_ROOT / "app" / "shared" / "web" / "static" / "js" / "navigation.js"


def test_shared_shell_has_local_styles_and_deferred_scripts() -> None:
    source = SHARED_LAYOUT.read_text(encoding="utf-8")

    for stylesheet in ("tokens", "reset", "layout", "components", "utilities"):
        assert f'/assets/css/{stylesheet}.css' in source
    assert 'src="/assets/js/app-shell.js?v={{ asset_version }}" defer' in source
    assert 'src="/assets/js/navigation.js?v={{ asset_version }}" defer' in source
    assert 'src="/assets/js/shell-navigation.js?v={{ asset_version }}" defer' in source
    assert 'src="/static/chat_realtime.js?v={{ asset_version }}" defer' in source


def test_shell_source_has_no_inline_handlers_or_navigation_emojis() -> None:
    source = SHARED_LAYOUT.read_text(encoding="utf-8")

    assert not re.search(r"\son(?:click|change|submit|input|keydown)=", source, re.IGNORECASE)
    for emoji in ("🏠", "💬", "👤", "🌐", "📊", "🏢", "🧩", "📄", "💰", "📦", "🏦", "🤝", "🛒", "📈", "⚙️", "🔐"):
        assert emoji not in source


def test_shell_exposes_accessible_navigation_contract() -> None:
    source = SHARED_LAYOUT.read_text(encoding="utf-8")

    for snippet in (
        'href="#main-content"',
        'id="main-content"',
        'aria-label="Navegação principal"',
        'aria-controls="primary-sidebar"',
        'aria-expanded="false"',
        'href="/opportunities"',
        'href="/cadastros/clients"',
        'href="/logout"',
        'data-nav-search',
    ):
        assert snippet in source


def test_shell_scripts_use_data_actions_and_persist_only_ui_preferences() -> None:
    shell_js = SHELL_SCRIPT.read_text(encoding="utf-8")
    navigation_js = NAVIGATION_SCRIPT.read_text(encoding="utf-8")

    assert "data-action" in shell_js
    assert "localStorage" in shell_js
    assert "sidebar-collapsed" in shell_js
    assert "data-nav-search" in navigation_js
    assert "data-nav-item" in navigation_js
    for forbidden in ("password", "token", "secret", "cookie"):
        assert forbidden not in shell_js.lower()


def test_authenticated_shell_marks_current_route_and_keeps_quick_actions(
    admin_client: TestClient,
) -> None:
    response = admin_client.get("/settings")

    assert response.status_code == 200
    assert 'href="/settings"' in response.text
    assert 'aria-current="page"' in response.text
    assert 'href="/opportunities"' in response.text
    assert 'href="/cadastros/clients"' in response.text


def test_legacy_base_is_a_compatibility_extension() -> None:
    source = COMPATIBILITY_LAYOUT.read_text(encoding="utf-8")

    assert '{% extends "layouts/base.html" %}' in source

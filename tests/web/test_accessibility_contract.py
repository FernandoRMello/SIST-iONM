import re
from pathlib import Path

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = REPO_ROOT / "app" / "templates"
SHARED_TEMPLATES = REPO_ROOT / "app" / "shared" / "web" / "templates"
SHARED_CSS = REPO_ROOT / "app" / "shared" / "web" / "static" / "css"
JAVASCRIPT_ROOTS = (
    REPO_ROOT / "app" / "static",
    REPO_ROOT / "app" / "shared" / "web" / "static" / "js",
)


def test_all_page_templates_are_local_and_inline_handler_free() -> None:
    pages = sorted(TEMPLATES.glob("*.html"))
    assert len(pages) == 25

    for page in pages:
        source = page.read_text(encoding="utf-8")
        assert not re.search(r"\son[a-z]+=", source, re.IGNORECASE), page.name
        assert not re.search(r"(?:https?:)?//(?!www\.w3\.org)", source), page.name
        assert not re.search(r'type="password"[^>]*value=', source, re.IGNORECASE), page.name
        assert not re.search(r"[\U0001F300-\U0001FAFF]", source), page.name
        if page.name != "base.html":
            assert "page_styles" in source, page.name
            assert "/assets/" in source, page.name


def test_shared_shell_uses_no_legacy_stylesheet_or_navigation_emoji() -> None:
    source = (SHARED_TEMPLATES / "layouts" / "base.html").read_text(encoding="utf-8")

    assert "/static/style.css" not in source
    assert not re.search(r"[\U0001F300-\U0001FAFF]", source)
    assert not (REPO_ROOT / "app" / "static" / "style.css").exists()


def test_shared_css_owns_shell_components_previously_in_legacy_css() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(SHARED_CSS.glob("*.css"))
    )

    for selector in (
        ".ui-page-header",
        ".ui-empty-state",
        ".money-sensitive",
        ".bitrix-chat-rail",
        ".bitrix-chat-panel",
        "body.bitrix-chat-open",
    ):
        assert selector in combined


def test_floating_chat_keeps_the_message_composer_inside_the_panel() -> None:
    source = (SHARED_CSS / "layout.css").read_text(encoding="utf-8")
    conversation_rule = re.search(
        r"\.bitrix-chat-conversation\s*\{(?P<body>[^}]*)\}",
        source,
    )

    assert conversation_rule is not None
    assert re.search(r"\bmin-height\s*:\s*0\s*;", conversation_rule.group("body"))


def test_javascript_avoids_dynamic_html_execution() -> None:
    sources = []
    for root in JAVASCRIPT_ROOTS:
        sources.extend(path.read_text(encoding="utf-8") for path in root.glob("*.js"))
    combined = "\n".join(sources)

    for forbidden in ("eval(", "document.write", "insertAdjacentHTML", ".innerHTML"):
        assert forbidden not in combined


def test_html_responses_include_baseline_security_headers(
    legacy_client: TestClient,
) -> None:
    response = legacy_client.get("/login")

    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]

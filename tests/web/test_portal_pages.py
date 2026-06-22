import re
from pathlib import Path

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = REPO_ROOT / "app" / "templates"
CHAT_JS = REPO_ROOT / "app" / "static" / "chat_realtime.js"
PORTAL_CSS = REPO_ROOT / "app" / "shared" / "web" / "static" / "css" / "portal.css"


def test_portal_templates_are_labelled_and_have_no_inline_handlers() -> None:
    names = ("feed.html", "chat.html", "profile.html", "orgchart.html")
    sources = {name: (TEMPLATES / name).read_text(encoding="utf-8") for name in names}

    for name, source in sources.items():
        assert not re.search(r"\son(?:click|change|submit|input)=", source, re.IGNORECASE), name
        assert "page_header" in source, name
    assert 'for="feed-content"' in sources["feed.html"]
    assert 'for="feed-attachment"' in sources["feed.html"]
    assert 'aria-live="polite"' in sources["chat.html"]
    assert "attachment_path" in sources["chat.html"]
    assert 'for="avatar"' in sources["profile.html"]
    assert "ui-org-fallback" in sources["orgchart.html"]


def test_portal_surfaces_render_with_accessible_landmarks(admin_client: TestClient) -> None:
    expectations = {
        "/feed": ("Feed da equipe", "Publicar"),
        "/chat": ("Conversas", "Chat em tempo real"),
        "/profile": ("Perfil do usuário", "Atualizar foto"),
        "/orgchart": ("Organograma", "Pessoas"),
    }
    for path, snippets in expectations.items():
        response = admin_client.get(path)
        assert response.status_code == 200
        assert '<main class="ui-content"' in response.text
        for snippet in snippets:
            assert snippet in response.text


def test_chat_script_uses_safe_dom_and_bounded_reconnection() -> None:
    source = CHAT_JS.read_text(encoding="utf-8")

    for snippet in ("new WebSocket", ".onopen", ".onclose", ".onerror", "textContent", "30000", "aria-live"):
        assert snippet in source
    assert "insertAdjacentHTML" not in source
    assert ".innerHTML" not in source
    assert "onclick=" not in source


def test_chat_script_preserves_conversation_context_and_attachments() -> None:
    source = CHAT_JS.read_text(encoding="utf-8")

    for snippet in (
        "bitrixChatTitle",
        "bitrixChatSubtitle",
        "classList.add('active')",
        "attachment_path",
        "attachment_is_image",
        "ui-message__image",
        "image.loading = 'lazy'",
    ):
        assert snippet in source
    assert "sistionm:content-updated" in source


def test_chat_notifications_are_assigned_to_the_sender_contact() -> None:
    source = CHAT_JS.read_text(encoding="utf-8")

    assert "badge.dataset.roomBadge = `user:${user.id}`" in source
    assert "`user:${payload.message.user_id}`" in source
    assert "state.unread[`user:${userId}`] = 0" in source


def test_both_chat_composers_offer_accessible_file_attachments() -> None:
    floating = (
        REPO_ROOT / "app" / "shared" / "web" / "templates" / "layouts" / "base.html"
    ).read_text(encoding="utf-8")
    full = (TEMPLATES / "chat.html").read_text(encoding="utf-8")

    for source, field_id in (
        (floating, "bitrixChatAttachment"),
        (full, "fullChatAttachment"),
    ):
        assert f'id="{field_id}"' in source
        assert 'name="attachment"' in source
        assert 'type="file"' in source
        assert f'for="{field_id}"' in source
    assert 'id="bitrixChatStatus"' in floating
    assert "['chatConnectionStatus', 'bitrixChatStatus']" in CHAT_JS.read_text(
        encoding="utf-8"
    )


def test_chat_window_uses_the_declared_grid_layout() -> None:
    source = PORTAL_CSS.read_text(encoding="utf-8")

    rule = re.search(r"\.ui-chat-window\s*\{(?P<body>[^}]*)\}", source)
    assert rule is not None
    assert "display: grid" in rule.group("body")

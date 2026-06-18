import re
import xml.etree.ElementTree as ET
from pathlib import Path

from app.main import SHARED_TEMPLATE_DIR, templates

REPO_ROOT = Path(__file__).resolve().parents[2]
SPRITE_PATH = REPO_ROOT / "app" / "shared" / "web" / "static" / "icons" / "sprite.svg"
MACROS_PATH = SHARED_TEMPLATE_DIR / "components" / "macros.html"

REQUIRED_ICON_IDS = {
    "dashboard",
    "feed",
    "chat",
    "user",
    "orgchart",
    "clients",
    "pipeline",
    "orders",
    "money",
    "products",
    "finance",
    "suppliers",
    "purchases",
    "bi",
    "sellers",
    "settings",
    "permissions",
    "search",
    "plus",
    "menu",
    "bell",
    "eye",
    "eye-off",
    "logout",
    "close",
    "arrow-left",
    "arrow-right",
}

REQUIRED_MACROS = {
    "icon",
    "page_header",
    "stat_card",
    "status_badge",
    "empty_state",
    "pagination",
    "form_field",
    "data_table_shell",
}


def test_local_sprite_contains_required_icons() -> None:
    root = ET.parse(SPRITE_PATH).getroot()
    symbol_ids = {
        element.attrib["id"]
        for element in root.findall("{http://www.w3.org/2000/svg}symbol")
    }

    assert symbol_ids >= REQUIRED_ICON_IDS


def test_shared_macro_file_declares_required_components() -> None:
    source = MACROS_PATH.read_text(encoding="utf-8")
    declared = set(re.findall(r"{%\s*macro\s+([a-z_]+)\(", source))

    assert declared >= REQUIRED_MACROS


def test_icon_macro_supports_decorative_and_labelled_output() -> None:
    template = templates.env.from_string(
        "{% from 'components/macros.html' import icon %}"
        "{{ icon('dashboard') }}{{ icon('bell', label='Notificações') }}"
    )
    rendered = template.render()

    assert 'href="/assets/icons/sprite.svg?v=20260618#dashboard"' in rendered
    assert 'aria-hidden="true"' in rendered
    assert 'role="img"' in rendered
    assert 'aria-label="Notificações"' in rendered


def test_choice_loader_resolves_legacy_and_shared_templates() -> None:
    assert templates.env.get_template("login.html") is not None
    assert templates.env.get_template("components/macros.html") is not None

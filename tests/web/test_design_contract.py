from pathlib import Path

from starlette.routing import Mount

from app.main import SHARED_STATIC_DIR, app

REPO_ROOT = Path(__file__).resolve().parents[2]
CSS_DIR = REPO_ROOT / "app" / "shared" / "web" / "static" / "css"
EXPECTED_CSS_FILES = {
    "tokens.css",
    "reset.css",
    "layout.css",
    "components.css",
    "utilities.css",
}


def test_shared_design_css_files_exist() -> None:
    actual_files = {path.name for path in CSS_DIR.glob("*.css")}

    assert actual_files == EXPECTED_CSS_FILES


def test_token_contract_matches_approved_foundation() -> None:
    tokens_css = (CSS_DIR / "tokens.css").read_text(encoding="utf-8")

    for token in (
        "--color-navy-950: #081426",
        "--color-teal-600: #0f8b8d",
        "--color-canvas: #f4f7fb",
        "--color-text: #172033",
        "--space-1: 4px",
        "--space-6: 24px",
    ):
        assert token in tokens_css


def test_css_foundation_includes_accessibility_and_stable_ui_contract() -> None:
    combined_css = "\n".join(
        (CSS_DIR / filename).read_text(encoding="utf-8")
        for filename in sorted(EXPECTED_CSS_FILES)
    )

    for snippet in (
        ":focus-visible",
        "prefers-reduced-motion",
        ".ui-shell",
        ".ui-button",
        ".ui-card",
        ".ui-table",
        ".ui-visually-hidden",
    ):
        assert snippet in combined_css


def test_assets_mount_uses_shared_static_directory_and_preserves_legacy_static() -> None:
    mounts = {
        route.path: route
        for route in app.routes
        if isinstance(route, Mount)
    }

    assert "/assets" in mounts
    assert Path(mounts["/assets"].app.directory) == SHARED_STATIC_DIR
    assert mounts["/assets"].name == "assets"

    assert "/static" in mounts
    assert mounts["/static"].name == "static"

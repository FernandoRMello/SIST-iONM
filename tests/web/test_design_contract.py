import re
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


def read_css(filename: str) -> str:
    return (CSS_DIR / filename).read_text(encoding="utf-8")


def read_combined_css() -> str:
    return "\n".join(
        read_css(filename)
        for filename in sorted(EXPECTED_CSS_FILES)
    )


def parse_color_tokens(css: str) -> dict[str, str]:
    return dict(re.findall(r"(--[\w-]+):\s*(#[0-9a-fA-F]{6})", css))


def extract_block(css: str, selector: str) -> str:
    start = css.find(selector)
    assert start != -1, f"missing selector block: {selector}"

    opening_brace = css.find("{", start)
    assert opening_brace != -1, f"missing opening brace for: {selector}"

    depth = 0
    for index in range(opening_brace, len(css)):
        character = css[index]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return css[opening_brace + 1:index]

    raise AssertionError(f"missing closing brace for: {selector}")


def extract_declaration(block: str, prop: str) -> str:
    match = re.search(rf"{re.escape(prop)}\s*:\s*([^;]+);", block)
    assert match, f"missing declaration: {prop}"
    return match.group(1).strip()


def relative_luminance(hex_color: str) -> float:
    hex_value = hex_color.removeprefix("#")
    channels = [int(hex_value[index:index + 2], 16) / 255 for index in (0, 2, 4)]

    def srgb_to_linear(channel: float) -> float:
        if channel <= 0.04045:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = [srgb_to_linear(channel) for channel in channels]
    return (0.2126 * red) + (0.7152 * green) + (0.0722 * blue)


def contrast_ratio(foreground: str, background: str) -> float:
    lighter = max(relative_luminance(foreground), relative_luminance(background))
    darker = min(relative_luminance(foreground), relative_luminance(background))
    return (lighter + 0.05) / (darker + 0.05)


def resolve_color_tokens(value: str, tokens: dict[str, str]) -> list[str]:
    token_names = re.findall(r"var\((--[\w-]+)\)", value)
    assert token_names, f"missing token references in value: {value}"
    return [tokens[name] for name in token_names]


def test_shared_design_css_files_exist() -> None:
    actual_files = {path.name for path in CSS_DIR.glob("*.css")}

    assert actual_files >= EXPECTED_CSS_FILES


def test_token_contract_matches_approved_foundation() -> None:
    tokens_css = read_css("tokens.css")

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
    combined_css = read_combined_css()

    for snippet in (
        ":focus-visible",
        "prefers-reduced-motion",
        ".ui-shell",
        ".ui-button",
        ".ui-card",
        ".ui-table",
        ".ui-visually-hidden",
        ".ui-shell--collapsed",
    ):
        assert snippet in combined_css


def test_primary_button_enabled_states_meet_wcag_aa_contrast() -> None:
    tokens = parse_color_tokens(read_css("tokens.css"))
    components_css = read_css("components.css")

    state_expectations = {
        ".ui-button--primary": "--color-text-inverse",
        ".ui-button--primary:hover": "--color-text-inverse",
        ".ui-button--primary:active": "--color-text-inverse",
    }

    for selector, foreground_token in state_expectations.items():
        block = extract_block(components_css, selector)
        background_colors = resolve_color_tokens(
            extract_declaration(block, "background"),
            tokens,
        )
        foreground = tokens[foreground_token]

        for background in background_colors:
            assert contrast_ratio(foreground, background) >= 4.5


def test_warning_semantic_text_meets_wcag_aa_on_soft_surface() -> None:
    tokens = parse_color_tokens(read_css("tokens.css"))

    assert contrast_ratio(tokens["--color-warning"], tokens["--color-warning-soft"]) >= 4.5


def test_reduced_motion_explicitly_disables_transform_movement() -> None:
    reset_css = read_css("reset.css")
    reduced_motion_block = extract_block(
        reset_css,
        "@media (prefers-reduced-motion: reduce)",
    )

    for selector in (
        ".ui-button:hover",
        ".ui-button:active",
        ".ui-card--interactive:hover",
    ):
        selector_block = extract_block(reduced_motion_block, selector)
        assert "transform: none !important;" in selector_block


def test_collapsed_shell_uses_desktop_collapsed_sidebar_width() -> None:
    layout_css = read_css("layout.css")
    desktop_block = extract_block(layout_css, "@media (min-width: 768px)")
    collapsed_shell_block = extract_block(desktop_block, ".ui-shell--collapsed")

    assert (
        "grid-template-columns: var(--sidebar-width-collapsed) minmax(0, 1fr);"
        in collapsed_shell_block
    )


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

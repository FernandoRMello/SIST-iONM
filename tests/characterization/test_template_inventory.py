from pathlib import Path

EXPECTED_TEMPLATES = {
    "access_profiles.html",
    "base.html",
    "bi_gerencial.html",
    "chat.html",
    "commissions.html",
    "crud.html",
    "dashboard.html",
    "feed.html",
    "finance.html",
    "hr_employees.html",
    "hr_payroll.html",
    "hr_rules.html",
    "login.html",
    "opportunities.html",
    "opportunity_card.html",
    "orders.html",
    "orgchart.html",
    "permissions.html",
    "profile.html",
    "purchases.html",
    "seller_reports.html",
    "settings.html",
    "whatsapp_settings.html",
}


def test_template_inventory_matches_legacy_surface_set() -> None:
    template_dir = Path(__file__).resolve().parents[2] / "app" / "templates"

    actual_templates = {path.name for path in template_dir.glob("*.html")}

    assert actual_templates == EXPECTED_TEMPLATES

from fastapi.routing import APIRoute

from app.main import app

EXPECTED_HTTP_ROUTES = {
    ("GET", "/"),
    ("GET", "/admin/permissions"),
    ("GET", "/backup/export-db"),
    ("GET", "/backoffice/purchases"),
    ("GET", "/bi-gerencial"),
    ("GET", "/cadastros/{table}"),
    ("GET", "/cadastros/{table}/delete/{record_id}"),
    ("GET", "/cadastros/{table}/edit/{record_id}"),
    ("GET", "/cadastros/{table}/import-template"),
    ("GET", "/chat"),
    ("GET", "/chat/context"),
    ("GET", "/chat/messages/{room_id}"),
    ("GET", "/chat/private-room/{other_user_id}"),
    ("GET", "/chat/private/{other_user_id}"),
    ("GET", "/commissions"),
    ("GET", "/favicon.ico"),
    ("GET", "/feed"),
    ("GET", "/feed/like/{post_id}"),
    ("GET", "/finance"),
    ("GET", "/login"),
    ("GET", "/logout"),
    ("GET", "/opportunities"),
    ("GET", "/opportunities/{opp_id}/card"),
    ("GET", "/opportunities/{opp_id}/make-order"),
    ("GET", "/opportunities/{opp_id}/move/{direction}"),
    ("GET", "/opportunities/{opp_id}/print-proposal"),
    ("GET", "/opportunities/{opp_id}/print-ro-supplier"),
    ("GET", "/opportunities/{opp_id}/proposal-pdf"),
    ("GET", "/opportunities/{opp_id}/ro-supplier-pdf"),
    ("GET", "/orders"),
    ("GET", "/orgchart"),
    ("GET", "/profile"),
    ("GET", "/reports/sellers"),
    ("GET", "/server-info"),
    ("GET", "/settings"),
    ("GET", "/settings/users/edit/{user_id}"),
    ("GET", "/settings/users/toggle/{user_id}"),
    ("POST", "/admin/permissions/save"),
    ("POST", "/backup/import-db"),
    ("POST", "/backoffice/purchases/add"),
    ("POST", "/cadastros/{table}/save-form"),
    ("POST", "/cadastros/{table}/import"),
    ("POST", "/chat/quick-send"),
    ("POST", "/chat/send"),
    ("POST", "/feed/comment/{post_id}"),
    ("POST", "/feed/post"),
    ("POST", "/finance/costs/add"),
    ("POST", "/login"),
    ("POST", "/opportunities/create"),
    ("POST", "/opportunities/{opp_id}/add-item"),
    ("POST", "/opportunities/{opp_id}/comment"),
    ("POST", "/opportunities/{opp_id}/document"),
    ("POST", "/opportunities/{opp_id}/note"),
    ("POST", "/orders/{order_id}/closing"),
    ("POST", "/profile/avatar"),
    ("POST", "/profile/save"),
    ("POST", "/reports/sellers/review"),
    ("POST", "/settings/role-email/save"),
    ("POST", "/settings/save"),
    ("POST", "/settings/users/create"),
    ("POST", "/settings/users/update/{user_id}"),
}

EXPECTED_WEBSOCKET_ROUTES = {"/ws/chat/{room_id}", "/ws/notify"}


def test_http_route_inventory_matches_legacy_contract() -> None:
    actual_routes = {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods
    }

    assert actual_routes == EXPECTED_HTTP_ROUTES


def test_websocket_route_inventory_matches_legacy_contract() -> None:
    actual_routes = {
        route.path for route in app.routes if route.__class__.__name__ == "APIWebSocketRoute"
    }

    assert actual_routes == EXPECTED_WEBSOCKET_ROUTES

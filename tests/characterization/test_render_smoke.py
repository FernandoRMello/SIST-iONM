import pytest
from fastapi.testclient import TestClient


def test_login_page_renders_with_named_credentials_fields(legacy_client: TestClient) -> None:
    response = legacy_client.get("/login")

    assert response.status_code == 200
    assert 'name="username"' in response.text
    assert 'name="password"' in response.text


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

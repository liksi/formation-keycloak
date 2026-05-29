from __future__ import annotations

import pytest
import requests

from conftest import (SECRET_WEBAPP_CLIENT, TEST_PASSWORD, TEST_USER,
                      _admin_headers, _client_secret)
from helpers.oidc import get_token

pytestmark = pytest.mark.usefixtures("seed_training_realm")


@pytest.mark.pw5
def test_pw5_api_requires_local_keycloak_token(
    keycloak_issuer,
    workspace_factory,
    process_manager,
):
    workspace = workspace_factory("pw5-api", "pw5_api_local_issuer")
    process_manager.start_api(workspace)

    public_response = requests.get("http://localhost:8091/messages/public", timeout=20)
    admin_unauthorized = requests.get(
        "http://localhost:8091/messages/admin", timeout=20
    )
    token = get_token(keycloak_issuer, "curl", TEST_USER, TEST_PASSWORD)
    admin_authorized = requests.get(
        "http://localhost:8091/messages/admin",
        headers={"Authorization": f"Bearer {token['access_token']}"},
        timeout=20,
    )

    assert public_response.status_code == 200
    assert admin_unauthorized.status_code == 401
    assert admin_authorized.status_code == 200
    assert admin_authorized.json()["message"] == "Hello Admin"


@pytest.mark.pw5
def test_pw5_api_user_endpoint_accepts_admin_or_user(
    keycloak_issuer,
    workspace_factory,
    process_manager,
):
    workspace = workspace_factory(
        "pw5-api-user", "pw5_api_local_issuer", "pw5_api_user_endpoint_roles"
    )
    process_manager.start_api(workspace)
    token = get_token(keycloak_issuer, "curl", TEST_USER, TEST_PASSWORD)

    response = requests.get(
        "http://localhost:8091/messages/user",
        headers={"Authorization": f"Bearer {token['access_token']}"},
        timeout=20,
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Hello User"


@pytest.mark.pw5
@pytest.mark.slow
def test_pw5_vue_can_login_and_call_api(
    keycloak_issuer,
    workspace_factory,
    process_manager,
):
    workspace = workspace_factory(
        "pw5-spa",
        "pw5_api_local_issuer",
        "pw5_api_user_endpoint_roles",
        "pw5_vue_login",
        "pw5_vue_bearer_token",
    )
    process_manager.start_api(workspace)
    process_manager.install_vue_dependencies(workspace)
    process_manager.start_vue_app(workspace)

    assert requests.get("http://localhost:8070/", timeout=20).status_code == 200
    assert _client_secret(_admin_headers(), SECRET_WEBAPP_CLIENT)


@pytest.mark.pw5
@pytest.mark.slow
def test_pw5_vue_full_login_and_api_call(
    browser,
    capture_page_artifacts,
    keycloak_issuer,
    workspace_factory,
    process_manager,
):
    workspace = workspace_factory(
        "pw5-spa-login",
        "pw5_api_local_issuer",
        "pw5_api_user_endpoint_roles",
        "pw5_vue_login",
        "pw5_vue_bearer_token",
    )
    process_manager.start_api(workspace)
    process_manager.install_vue_dependencies(workspace)
    process_manager.start_vue_app(workspace)

    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    page.set_default_timeout(30_000)
    capture_page_artifacts(page, "vue-full-login")
    try:
        page.goto("http://localhost:8070/", wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")

        assert "localhost:8080" in page.url, "Vue app should redirect to Keycloak login"

        page.get_by_role("textbox", name="Username or email").fill(TEST_USER)
        page.get_by_role("textbox", name="Password").fill(TEST_PASSWORD)
        page.get_by_role("button", name="Sign In").click()
        page.wait_for_load_state("networkidle")

        assert "localhost:8070" in page.url, "Should redirect back to Vue app after login"

        page.wait_for_selector('[data-testid="fetch-btn-admin"]', state="visible")
        page.click('[data-testid="fetch-btn-admin"]')
        page.wait_for_function(
            'document.querySelector(\'[data-testid="fetch-result-admin"]\')?.textContent?.trim()',
            timeout=10_000,
        )

        result_text = page.text_content('[data-testid="fetch-result-admin"]')
        assert "Hello Admin" in result_text, (
            f"Expected 'Hello Admin' in API response, got: {result_text!r}"
        )
    finally:
        context.close()


@pytest.mark.pw5
@pytest.mark.slow
def test_pw5_vue_bearer_token_in_request(
    browser,
    capture_page_artifacts,
    keycloak_issuer,
    workspace_factory,
    process_manager,
):
    workspace = workspace_factory(
        "pw5-spa-bearer",
        "pw5_api_local_issuer",
        "pw5_api_user_endpoint_roles",
        "pw5_vue_login",
        "pw5_vue_bearer_token",
    )
    process_manager.start_api(workspace)
    process_manager.install_vue_dependencies(workspace)
    process_manager.start_vue_app(workspace)

    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    page.set_default_timeout(30_000)
    capture_page_artifacts(page, "vue-bearer-token")

    api_requests_with_auth: list = []
    page.on(
        "request",
        lambda r: api_requests_with_auth.append(r)
        if "localhost:8091/messages" in r.url and r.headers.get("authorization", "").startswith("Bearer ")
        else None,
    )

    try:
        page.goto("http://localhost:8070/", wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.get_by_role("textbox", name="Username or email").fill(TEST_USER)
        page.get_by_role("textbox", name="Password").fill(TEST_PASSWORD)
        page.get_by_role("button", name="Sign In").click()
        page.wait_for_load_state("networkidle")

        page.wait_for_selector('[data-testid="fetch-btn-admin"]', state="visible")
        page.click('[data-testid="fetch-btn-admin"]')
        page.wait_for_function(
            'document.querySelector(\'[data-testid="fetch-result-admin"]\')?.textContent?.trim()',
            timeout=10_000,
        )

        assert api_requests_with_auth, (
            "Expected at least one API request to /messages/admin with Authorization: Bearer header"
        )
    finally:
        context.close()

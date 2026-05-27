from __future__ import annotations

import pytest
import requests

from conftest import (CURL_CLIENT, KEYCLOAK_URL, REALM_NAME,
                      SECRET_WEBAPP_CLIENT, TEST_PASSWORD, TEST_USER,
                      _admin_headers, _client_secret, _update_client, _user_id)
from helpers.oidc import (decode_jwt, get_openid_configuration, get_token,
                          refresh_token, userinfo)

pytestmark = pytest.mark.usefixtures("seed_training_realm")


@pytest.mark.pw2
def test_pw2_discovery_and_password_grant(keycloak_issuer):
    config = get_openid_configuration(keycloak_issuer)
    token_response = get_token(keycloak_issuer, CURL_CLIENT, TEST_USER, TEST_PASSWORD)
    access_token = decode_jwt(token_response["access_token"])

    assert config["issuer"] == keycloak_issuer
    assert config["token_endpoint"].startswith(keycloak_issuer)
    assert token_response["refresh_token"]
    assert token_response["session_state"]
    assert access_token["preferred_username"] == TEST_USER
    assert access_token["sub"]


@pytest.mark.pw2
def test_pw2_refresh_and_userinfo_scope_behavior(keycloak_issuer):
    token_response = get_token(keycloak_issuer, CURL_CLIENT, TEST_USER, TEST_PASSWORD)
    refreshed = refresh_token(
        keycloak_issuer, CURL_CLIENT, token_response["refresh_token"]
    )
    without_openid = userinfo(keycloak_issuer, token_response["access_token"])
    with_openid = get_token(
        keycloak_issuer,
        CURL_CLIENT,
        TEST_USER,
        TEST_PASSWORD,
        scope="openid",
    )
    with_openid_userinfo = userinfo(keycloak_issuer, with_openid["access_token"])

    assert refreshed["access_token"] != token_response["access_token"]
    assert without_openid.status_code >= 400
    assert with_openid_userinfo.status_code == 200
    assert with_openid_userinfo.json()["preferred_username"] == TEST_USER


@pytest.mark.pw2
@pytest.mark.slow
def test_pw2_sso_no_reauth_with_existing_session(
    browser,
    capture_page_artifacts,
    workspace_factory,
    workspace_manager,
    process_manager,
):
    headers = _admin_headers()
    _update_client(headers, SECRET_WEBAPP_CLIENT, consentRequired=False)
    workspace = workspace_factory("pw2-sso-no-reauth", "pw2_secret_webapp_local_keycloak")
    workspace_manager.replace(
        workspace,
        "secret-webapp/src/main/resources/application-keycloak.yml",
        "client-secret: hC0VxkSVOkxzAewulJ2arhfKTYNOWYOQ",
        f"client-secret: {_client_secret(headers, SECRET_WEBAPP_CLIENT)}",
    )
    process_manager.start_secret_webapp(workspace)

    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    page.set_default_timeout(20_000)
    capture_page_artifacts(page, "sso-no-reauth-first")
    try:
        page.goto("http://localhost:8090/secret/index.html", wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.get_by_role("textbox", name="Username or email").fill(TEST_USER)
        page.get_by_role("textbox", name="Password").fill(TEST_PASSWORD)
        page.get_by_role("button", name="Sign In").click()
        page.wait_for_load_state("networkidle")
        assert "localhost:8090" in page.url, "First login should redirect back to app"
        assert "Keycloak rocks" in page.content()

        page2 = context.new_page()
        capture_page_artifacts(page2, "sso-no-reauth-second")
        page2.goto("http://localhost:8090/secret/index.html", wait_until="domcontentloaded")
        page2.wait_for_load_state("networkidle")

        assert "localhost:8090" in page2.url, (
            "SSO: second tab in same browser context should reach app without KC redirect"
        )
        assert "Keycloak rocks" in page2.content()
    finally:
        context.close()


@pytest.mark.pw2
def test_pw2_sso_logout_clears_session(keycloak_issuer):
    headers = _admin_headers()
    token = get_token(keycloak_issuer, CURL_CLIENT, TEST_USER, TEST_PASSWORD)

    uid = _user_id(headers, TEST_USER)
    sessions = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users/{uid}/sessions",
        headers=headers,
        timeout=30,
    )
    sessions.raise_for_status()
    assert len(sessions.json()) > 0, "Expected active KC session after login"

    requests.delete(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users/{uid}/sessions",
        headers=headers,
        timeout=30,
    ).raise_for_status()

    refresh_resp = requests.post(
        f"{keycloak_issuer}/protocol/openid-connect/token",
        data={
            "client_id": CURL_CLIENT,
            "grant_type": "refresh_token",
            "refresh_token": token["refresh_token"],
        },
        timeout=30,
    )
    assert refresh_resp.status_code == 400, (
        "Refresh token should be invalid after KC session is terminated (SSO logout)"
    )

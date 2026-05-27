from __future__ import annotations

import contextlib
import http.server
import socketserver
import threading

import pytest
import requests

from conftest import (CURL_CLIENT, KEYCLOAK_URL, MAILDEV_URL, REALM_NAME,
                      SECRET_WEBAPP_CLIENT, TEST_PASSWORD, TEST_USER,
                      _add_required_action_api, _add_user_to_group_api,
                      _admin_headers, _assign_role_to_group_api,
                      _client_secret, _configure_smtp_api, _ensure_client,
                      _ensure_client_scope_assigned, _ensure_group,
                      _ensure_role, _ensure_user,
                      _ensure_user_profile_attribute, _set_password_policy_api,
                      _set_user_attribute_api, _trigger_actions_email_api,
                      _update_client, _user_id)
from helpers.maildev import wait_for_message
from helpers.oidc import decode_jwt, get_token

pytestmark = pytest.mark.usefixtures("seed_training_realm")


@pytest.mark.pw3
def test_pw3_secret_webapp_can_delegate_to_local_keycloak(
    workspace_factory,
    workspace_manager,
    process_manager,
):
    headers = _admin_headers()
    workspace = workspace_factory(
        "pw3-secret-webapp", "pw2_secret_webapp_local_keycloak"
    )
    workspace_manager.replace(
        workspace,
        "secret-webapp/src/main/resources/application-keycloak.yml",
        "client-secret: hC0VxkSVOkxzAewulJ2arhfKTYNOWYOQ",
        f"client-secret: {_client_secret(headers, SECRET_WEBAPP_CLIENT)}",
    )

    process_manager.start_secret_webapp(workspace)
    response = requests.get(
        "http://localhost:8090/secret/index.html", timeout=20, allow_redirects=False
    )
    intermediate_location = response.headers["Location"]
    if intermediate_location.startswith("http://") or intermediate_location.startswith(
        "https://"
    ):
        intermediate_url = intermediate_location
    else:
        intermediate_url = f"http://localhost:8090{intermediate_location}"
    keycloak_redirect = requests.get(
        intermediate_url, timeout=20, allow_redirects=False
    )

    assert response.status_code in (302, 303)
    assert response.headers["Location"].endswith("/oauth2/authorization/keycloak")
    assert (
        f"{KEYCLOAK_URL}/realms/{REALM_NAME}" in keycloak_redirect.headers["Location"]
    )


@pytest.mark.pw3
def test_pw3_group_and_role_mapping_flow(admin_page):
    headers = _admin_headers()
    _ensure_group(headers, "Admins")
    _ensure_user(
        headers,
        "admin_user",
        "pwd",
        email="admin_user@example.com",
        first_name="Admin",
        last_name="User",
    )
    _ensure_role(headers, "ROLE_MANAGER")
    _assign_role_to_group_api(headers, "Admins", "ROLE_MANAGER")
    _add_user_to_group_api(headers, "admin_user", "Admins")
    _add_required_action_api(headers, "admin_user", "UPDATE_PASSWORD")

    user_response = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users",
        headers=headers,
        params={"username": "admin_user"},
        timeout=20,
    )
    user_response.raise_for_status()
    user = next(
        item for item in user_response.json() if item["username"] == "admin_user"
    )

    groups_response = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users/{user['id']}/groups",
        headers=headers,
        timeout=20,
    )
    groups_response.raise_for_status()

    assert "UPDATE_PASSWORD" in user["requiredActions"]
    assert any(group["name"] == "Admins" for group in groups_response.json())


@pytest.mark.pw3
def test_pw3_password_policy_email_and_claims(admin_page, keycloak_issuer):
    headers = _admin_headers()
    _set_password_policy_api(headers, "length(10) and digits(1) and specialChars(1)")
    _configure_smtp_api(
        headers, host="smtp", port="1025", from_addr="keycloak@formation.lan"
    )
    _ensure_user(
        headers,
        "emailuser",
        "Longpass1!",
        email="emailuser@example.com",
        first_name="Email",
        last_name="User",
    )
    _add_required_action_api(headers, "emailuser", "VERIFY_EMAIL")
    _trigger_actions_email_api(headers, "emailuser", ["VERIFY_EMAIL"])
    _ensure_user_profile_attribute(headers, "phoneNumber", display_name="phoneNumber")
    _ensure_user_profile_attribute(
        headers, "phoneNumberVerified", display_name="phoneNumberVerified"
    )
    _set_user_attribute_api(headers, TEST_USER, "phoneNumber", "+33612345678")
    _update_client(
        headers,
        SECRET_WEBAPP_CLIENT,
        consentRequired=True,
        rootUrl="http://localhost:8090",
        baseUrl="http://localhost:8090",
    )
    _ensure_client_scope_assigned(headers, "curl", "phone", optional=True)

    token = get_token(
        keycloak_issuer, "curl", TEST_USER, TEST_PASSWORD, scope="openid phone"
    )
    claims = decode_jwt(token["id_token"])
    message = wait_for_message("emailuser@example.com", MAILDEV_URL)

    assert claims["phone_number"] == "+33612345678"
    assert message["to"][0]["address"] == "emailuser@example.com"


@pytest.mark.pw3
def test_pw3_admin_page_accessible_with_role(
    browser, capture_page_artifacts, workspace_factory, workspace_manager, process_manager
):
    headers = _admin_headers()
    _update_client(headers, SECRET_WEBAPP_CLIENT, consentRequired=False)
    workspace = workspace_factory("pw3-admin-access", "pw2_secret_webapp_local_keycloak")
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
    capture_page_artifacts(page, "admin-access")
    try:
        page.goto("http://localhost:8090/admin/index.html", wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.get_by_role("textbox", name="Username or email").fill(TEST_USER)
        page.get_by_role("textbox", name="Password").fill(TEST_PASSWORD)
        page.get_by_role("button", name="Sign In").click()
        page.wait_for_load_state("networkidle")

        assert "admin area" in page.content().lower(), (
            "User with ROLE_ADMIN should be able to access the admin page"
        )
    finally:
        context.close()


@pytest.mark.pw3
def test_pw3_admin_page_blocked_without_role(
    browser, capture_page_artifacts, workspace_factory, workspace_manager, process_manager
):
    headers = _admin_headers()
    _update_client(headers, SECRET_WEBAPP_CLIENT, consentRequired=False)
    _ensure_user(
        headers,
        "norole_user",
        "NoRolePass1!",
        email="norole@example.com",
        first_name="No",
        last_name="Role",
    )
    workspace = workspace_factory("pw3-admin-blocked", "pw2_secret_webapp_local_keycloak")
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
    capture_page_artifacts(page, "admin-blocked")
    try:
        page.goto("http://localhost:8090/admin/index.html", wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.get_by_role("textbox", name="Username or email").fill("norole_user")
        page.get_by_role("textbox", name="Password").fill("NoRolePass1!")
        page.get_by_role("button", name="Sign In").click()
        page.wait_for_load_state("networkidle")

        page_body = page.content()
        assert (
            "403" in page_body or "Forbidden" in page_body or "Access Denied" in page_body
        ), "User without ROLE_ADMIN should be denied access to the admin page"
    finally:
        context.close()


@pytest.mark.pw3
def test_pw3_password_policy_rejects_weak_password():
    headers = _admin_headers()
    _set_password_policy_api(headers, "length(10) and digits(1) and specialChars(1)")
    _ensure_user(
        headers,
        "policy_test_user",
        "ValidPass1!",
        email="policytest@example.com",
        first_name="Policy",
        last_name="Test",
    )
    uid = _user_id(headers, "policy_test_user")

    weak_resp = requests.put(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users/{uid}/reset-password",
        headers=headers,
        json={"type": "password", "value": "weak", "temporary": False},
        timeout=30,
    )
    assert weak_resp.status_code == 400, (
        f"Expected 400 (policy violation) for weak password, got {weak_resp.status_code}: {weak_resp.text}"
    )


@pytest.mark.pw3
def test_pw3_required_action_update_password_redirects(browser, capture_page_artifacts):
    headers = _admin_headers()
    _ensure_user(
        headers,
        "update_pw_user",
        "UpdatePass1!",
        email="updatepw@example.com",
        first_name="Update",
        last_name="PwUser",
    )
    _add_required_action_api(headers, "update_pw_user", "UPDATE_PASSWORD")

    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    page.set_default_timeout(20_000)
    capture_page_artifacts(page, "update-password-required")
    try:
        auth_url = (
            f"{KEYCLOAK_URL}/realms/{REALM_NAME}/protocol/openid-connect/auth"
            "?client_id=curl&response_type=code&scope=openid"
            "&redirect_uri=http://localhost:9999/"
        )
        page.goto(auth_url, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.get_by_role("textbox", name="Username or email").fill("update_pw_user")
        page.get_by_role("textbox", name="Password").fill("UpdatePass1!")
        page.get_by_role("button", name="Sign In").click()
        page.wait_for_load_state("networkidle")

        assert "localhost:9999" not in page.url, (
            "Required action should intercept the flow before redirect to client"
        )
        page_text = page.content().lower()
        assert (
            "update password" in page_text
            or "new password" in page_text
            or "change password" in page_text
        ), "KC should show the Update Password form for users with UPDATE_PASSWORD required action"
    finally:
        context.close()


@pytest.mark.pw3
def test_pw3_required_action_verify_email_redirects(browser, capture_page_artifacts):
    headers = _admin_headers()
    _configure_smtp_api(headers, host="smtp", port="1025", from_addr="keycloak@formation.lan")
    _ensure_user(
        headers,
        "verify_email_user",
        "VerifyEmail1!",
        email="verifyemail@example.com",
        first_name="Verify",
        last_name="EmailUser",
    )
    _add_required_action_api(headers, "verify_email_user", "VERIFY_EMAIL")

    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    page.set_default_timeout(20_000)
    capture_page_artifacts(page, "verify-email-required")
    try:
        auth_url = (
            f"{KEYCLOAK_URL}/realms/{REALM_NAME}/protocol/openid-connect/auth"
            "?client_id=curl&response_type=code&scope=openid"
            "&redirect_uri=http://localhost:9999/"
        )
        page.goto(auth_url, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.get_by_role("textbox", name="Username or email").fill("verify_email_user")
        page.get_by_role("textbox", name="Password").fill("VerifyEmail1!")
        page.get_by_role("button", name="Sign In").click()
        page.wait_for_load_state("networkidle")

        assert "localhost:9999" not in page.url, (
            "Required action should intercept the flow before redirect to client"
        )
        page_text = page.content().lower()
        assert (
            "verify" in page_text and "email" in page_text
        ), "KC should show the Verify Email page for users with VERIFY_EMAIL required action"
    finally:
        context.close()


@pytest.mark.pw3
def test_pw3_custom_scope_company_claims_id_token_only(keycloak_issuer):
    headers = _admin_headers()

    scopes_resp = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/client-scopes",
        headers=headers,
        timeout=30,
    )
    scopes_resp.raise_for_status()
    company_scope = next((s for s in scopes_resp.json() if s["name"] == "company"), None)
    if company_scope is None:
        requests.post(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/client-scopes",
            headers=headers,
            json={
                "name": "company",
                "protocol": "openid-connect",
                "attributes": {
                    "include.in.token.scope": "true",
                    "display.on.consent.screen": "true",
                },
            },
            timeout=30,
        ).raise_for_status()
        scopes_resp = requests.get(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/client-scopes",
            headers=headers,
            timeout=30,
        )
        scopes_resp.raise_for_status()
        company_scope = next(s for s in scopes_resp.json() if s["name"] == "company")
    scope_id = company_scope["id"]

    mappers_resp = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/client-scopes/{scope_id}/protocol-mappers/models",
        headers=headers,
        timeout=30,
    )
    mappers_resp.raise_for_status()
    if not any(m["name"] == "company-name" for m in mappers_resp.json()):
        requests.post(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/client-scopes/{scope_id}/protocol-mappers/models",
            headers=headers,
            json={
                "name": "company-name",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-usermodel-attribute-mapper",
                "consentRequired": False,
                "config": {
                    "user.attribute": "companyName",
                    "claim.name": "company_name",
                    "id.token.claim": "true",
                    "access.token.claim": "false",
                    "userinfo.token.claim": "false",
                    "jsonType.label": "String",
                },
            },
            timeout=30,
        ).raise_for_status()

    _ensure_user_profile_attribute(headers, "companyName", display_name="Company Name")
    _set_user_attribute_api(headers, TEST_USER, "companyName", "Liksi")
    _ensure_client_scope_assigned(headers, CURL_CLIENT, "company", optional=True)

    token = get_token(keycloak_issuer, CURL_CLIENT, TEST_USER, TEST_PASSWORD, scope="openid company")
    id_claims = decode_jwt(token["id_token"])
    access_claims = decode_jwt(token["access_token"])

    assert id_claims.get("company_name") == "Liksi", (
        "company_name claim must be present in ID token"
    )
    assert "company_name" not in access_claims, (
        "company_name claim must not be present in access token (id_token only mapper)"
    )


@pytest.mark.pw3
def test_pw3_consent_screen_appears_on_first_login(browser, capture_page_artifacts):
    headers = _admin_headers()
    _ensure_client(
        headers,
        "consent-test-client",
        public=True,
        redirect_uris=["http://localhost:9999/*"],
    )
    _update_client(headers, "consent-test-client", consentRequired=True)
    _ensure_user(
        headers,
        "consent_user",
        "ConsentPass1!",
        email="consent@example.com",
        first_name="Consent",
        last_name="User",
    )

    # KC redirects the browser to redirect_uri?code=... after consent.
    # Playwright would throw "connection refused" if nothing is listening on that port.
    # We spin up a minimal HTTP server on 9999 to receive the redirect and capture the code.
    class _ConsentCallbackHandler(http.server.BaseHTTPRequestHandler):
        callback_path: str | None = None

        def do_GET(self):
            type(self).callback_path = self.path
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<html><body>Consent callback received</body></html>")

        def log_message(self, format, *args):
            return

    with socketserver.TCPServer(("127.0.0.1", 9999), _ConsentCallbackHandler) as server:
        server.timeout = 0.5
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        auth_url = (
        f"{KEYCLOAK_URL}/realms/{REALM_NAME}/protocol/openid-connect/auth"
        "?client_id=consent-test-client&response_type=code&scope=openid"
        "&redirect_uri=http://localhost:9999/"
        )

        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.set_default_timeout(20_000)
        capture_page_artifacts(page, "consent-screen")
        try:
            page.goto(auth_url, wait_until="domcontentloaded")
            page.wait_for_load_state("networkidle")
            page.get_by_role("textbox", name="Username or email").fill("consent_user")
            page.get_by_role("textbox", name="Password").fill("ConsentPass1!")
            page.get_by_role("button", name="Sign In").click()
            page.wait_for_load_state("networkidle")

            page_content = page.content().lower()
            assert any(
                word in page_content for word in ["consent", "grant", "allow", "access"]
            ), "Consent screen should appear after login for consentRequired client"

            consent_button = (
                page.get_by_role("button", name="Allow")
                .or_(page.get_by_role("button", name="Continue"))
                .or_(page.get_by_role("button", name="Yes"))
                .or_(page.locator("button[type='submit']").first)
            )
            with contextlib.suppress(Exception):
                with page.expect_navigation(wait_until="load", timeout=10_000):
                    consent_button.click()

            page.wait_for_url("http://localhost:9999/**", timeout=10_000)
            assert "localhost:9999" in page.url, (
                "After granting consent, KC should redirect to the configured redirect_uri"
            )
            assert "code=" in page.url, "Authorization code should be present in redirect URL"
            assert _ConsentCallbackHandler.callback_path is not None
            assert "code=" in _ConsentCallbackHandler.callback_path
        finally:
            context.close()
            server.shutdown()
            thread.join(timeout=2)


@pytest.mark.pw3
def test_pw3_phone_number_verified_claim(keycloak_issuer):
    headers = _admin_headers()
    # KC 26 User Profile: custom attributes must be declared in the realm schema before
    # they can be set on users. Without this, the attribute is silently dropped on PUT.
    _ensure_user_profile_attribute(headers, "phoneNumber", display_name="phoneNumber")
    _ensure_user_profile_attribute(headers, "phoneNumberVerified", display_name="phoneNumberVerified")
    _set_user_attribute_api(headers, TEST_USER, "phoneNumber", "+33612345678")
    _set_user_attribute_api(headers, TEST_USER, "phoneNumberVerified", "true")
    _ensure_client_scope_assigned(headers, CURL_CLIENT, "phone", optional=True)

    token = get_token(keycloak_issuer, CURL_CLIENT, TEST_USER, TEST_PASSWORD, scope="openid phone")
    claims = decode_jwt(token["access_token"])

    assert claims.get("phone_number") == "+33612345678", (
        "phone_number claim must be present in access token when phone scope is requested"
    )
    assert claims.get("phone_number_verified") is True or claims.get("phone_number_verified") == "true", (
        "phone_number_verified claim must reflect the user's phoneNumberVerified attribute"
    )

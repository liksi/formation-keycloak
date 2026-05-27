from __future__ import annotations

import time

import pytest
import requests

from conftest import (KEYCLOAK_URL, OAUTH2_PROXY_CLIENT, REALM_NAME,
                      TEST_PASSWORD, TEST_USER, _admin_headers, _client_secret,
                      _ensure_client, _ensure_client_protocol_mapper)
from helpers.keycloak_ui import add_ldap_federation, sync_ldap_users
from helpers.keycloak_ui import \
    test_ldap_connection as run_ldap_connection_check
from helpers.ldap import LDAPManager
from helpers.stack import DockerStack

pytestmark = pytest.mark.usefixtures("seed_training_realm")


@pytest.mark.pw6
def test_pw6_events_and_ldap_federation(admin_page):
    headers = _admin_headers()
    events_response = requests.put(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/events/config",
        headers=headers,
        json={
            "eventsEnabled": True,
            "adminEventsEnabled": True,
            "adminEventsDetailsEnabled": True,
            "enabledEventTypes": ["LOGIN", "LOGIN_ERROR", "LOGOUT"],
        },
        timeout=30,
    )
    events_response.raise_for_status()

    ldap = LDAPManager(
        "ldap://localhost:389", "cn=admin,dc=formation", "admin", "dc=formation"
    )
    ldap.create_group("users")
    ldap.create_user("ldap-user", "User", uid="ldap-user", password="pwd")
    ldap.add_user_to_group("ldap-user", "users")

    add_ldap_federation(
        admin_page,
        {
            "vendor": "other",
            "connectionUrl": "ldap://openldap",
            "usersDn": "dc=formation",
            "bindDn": "cn=admin,dc=formation",
            "bindCredential": "admin",
            "editMode": "READ_ONLY",
        },
    )
    run_ldap_connection_check(admin_page)
    sync_ldap_users(admin_page)

    assert ldap.get_users()


@pytest.mark.pw6
@pytest.mark.slow
def test_pw6_oauth2_proxy_uses_lab_compose(
    browser,
    capture_page_artifacts,
    workspace_factory,
    workspace_manager,
    process_manager,
):
    headers = _admin_headers()
    _ensure_client(
        headers,
        OAUTH2_PROXY_CLIENT,
        public=False,
        redirect_uris=["http://localhost:4180/oauth2/callback"],
    )
    _ensure_client_protocol_mapper(
        headers,
        OAUTH2_PROXY_CLIENT,
        "oauth2-proxy-audience",
        "oidc-audience-mapper",
        {
            "included.client.audience": OAUTH2_PROXY_CLIENT,
            "id.token.claim": "true",
            "access.token.claim": "true",
            "included.custom.audience": "",
        },
    )
    client_secret = _client_secret(headers, OAUTH2_PROXY_CLIENT)

    workspace = workspace_factory("pw6-oauth2-proxy", "pw6_oauth2_proxy_compose")
    workspace_manager.replace(
        workspace,
        "docker-compose.yml",
        '      OAUTH2_PROXY_CLIENT_SECRET: "PVIrotLG3RhMifMKu9MCaHmpMj81x5JD"',
        f'      OAUTH2_PROXY_CLIENT_SECRET: "{client_secret}"',
    )
    workspace_manager.replace(
        workspace,
        "docker-compose.yml",
        '      OAUTH2_PROXY_OIDC_ISSUER_URL: "http://localhost:8080/realms/master"',
        '      OAUTH2_PROXY_OIDC_ISSUER_URL: "http://localhost:8080/realms/training"',
    )

    process_manager.start_secret_webapp(workspace)
    workspace_stack = DockerStack(workspace)
    workspace_stack.rm("oauth2-proxy")
    workspace_stack.up_no_deps("oauth2-proxy")
    try:
        protected_url = "http://localhost:4180/secret/index.html"
        deadline = time.monotonic() + 60
        response = None
        while time.monotonic() < deadline:
            try:
                candidate = requests.get(
                    protected_url, timeout=5, allow_redirects=False
                )
                if candidate.status_code in (302, 303):
                    response = candidate
                    break
            except requests.RequestException:
                pass
            time.sleep(1)

        assert response is not None, workspace_stack.logs("oauth2-proxy", tail=200)
        assert response.status_code in (302, 303)
        location = response.headers["Location"]
        assert location.startswith(
            "http://localhost:8080/realms/training/protocol/openid-connect/auth"
        )
        assert "client_id=oauth2-proxy" in location
        assert (
            "redirect_uri=http%3A%2F%2Flocalhost%3A4180%2Foauth2%2Fcallback" in location
        )

        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.set_default_timeout(20_000)
        capture_page_artifacts(page, "oauth2-proxy")
        page.goto(protected_url, wait_until="domcontentloaded")
        page.get_by_role("textbox", name="Username or email").fill(TEST_USER)
        page.get_by_role("textbox", name="Password").fill(TEST_PASSWORD)
        page.get_by_role("button", name="Sign In").click()
        page.wait_for_load_state("networkidle")
        assert page.get_by_role("heading", name="Keycloak rocks !").count() == 1
        context.close()
    finally:
        workspace_stack.rm("oauth2-proxy")

from __future__ import annotations

import time

import pytest
import requests

from conftest import (CURL_CLIENT, KEYCLOAK_URL, OAUTH2_PROXY_CLIENT,
                      REALM_NAME, TEST_PASSWORD, TEST_USER, _admin_headers,
                      _assign_role_to_user_api, _client_secret, _ensure_client,
                      _ensure_client_protocol_mapper, _ensure_role, _ensure_user)
from helpers.keycloak_ui import add_ldap_federation, sync_ldap_users
from helpers.keycloak_ui import \
    test_ldap_connection as run_ldap_connection_check
from helpers.ldap import LDAPManager
from helpers.oidc import get_token
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


@pytest.mark.pw6
def test_pw6_login_event_appears_in_events_list(keycloak_issuer):
    headers = _admin_headers()
    requests.put(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/events/config",
        headers=headers,
        json={
            "eventsEnabled": True,
            "adminEventsEnabled": True,
            "adminEventsDetailsEnabled": True,
            "enabledEventTypes": ["LOGIN", "LOGIN_ERROR", "LOGOUT"],
        },
        timeout=30,
    ).raise_for_status()

    get_token(keycloak_issuer, CURL_CLIENT, TEST_USER, TEST_PASSWORD)
    time.sleep(1)

    events_resp = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/events",
        headers=headers,
        params={"type": "LOGIN"},
        timeout=30,
    )
    events_resp.raise_for_status()
    events = events_resp.json()

    assert any(e["type"] == "LOGIN" for e in events), (
        "Expected at least one LOGIN event to be recorded after authenticating"
    )


@pytest.mark.pw6
def test_pw6_ldap_user_can_login(keycloak_issuer):
    """LDAP-synced users can authenticate against Keycloak using their LDAP credentials."""
    headers = _admin_headers()

    ldap = LDAPManager(
        "ldap://localhost:389", "cn=admin,dc=formation", "admin", "dc=formation"
    )
    ldap.create_group("users")
    ldap.create_user("ldap-user", "User", uid="ldap-user", password="pwd")

    comp_resp = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/components"
        "?type=org.keycloak.storage.UserStorageProvider",
        headers=headers,
        timeout=30,
    )
    comp_resp.raise_for_status()
    existing_fed = next(
        (c for c in comp_resp.json() if c.get("providerId") == "ldap"), None
    )
    if existing_fed is None:
        requests.post(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/components",
            headers=headers,
            json={
                "name": "ldap",
                "providerId": "ldap",
                "providerType": "org.keycloak.storage.UserStorageProvider",
                "config": {
                    "vendor": ["other"],
                    "connectionUrl": ["ldap://openldap"],
                    "bindDn": ["cn=admin,dc=formation"],
                    "bindCredential": ["admin"],
                    "usersDn": ["dc=formation"],
                    "usernameLDAPAttribute": ["uid"],
                    "rdnLDAPAttribute": ["uid"],
                    "uuidLDAPAttribute": ["entryUUID"],
                    "userObjectClasses": ["inetOrgPerson"],
                    "authType": ["simple"],
                    "editMode": ["READ_ONLY"],
                    "syncRegistrations": ["false"],
                    "importEnabled": ["true"],
                    "pagination": ["true"],
                    "enabled": ["true"],
                },
            },
            timeout=30,
        ).raise_for_status()
        comp_resp = requests.get(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/components"
            "?type=org.keycloak.storage.UserStorageProvider",
            headers=headers,
            timeout=30,
        )
        comp_resp.raise_for_status()
        existing_fed = next(c for c in comp_resp.json() if c.get("providerId") == "ldap")

    fed_id = existing_fed["id"]
    requests.post(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/user-storage/{fed_id}/sync"
        "?action=triggerFullSync",
        headers=headers,
        timeout=60,
    ).raise_for_status()

    token = get_token(keycloak_issuer, CURL_CLIENT, "ldap-user", "pwd")
    assert token.get("access_token"), "LDAP user should receive a valid access token"


@pytest.mark.pw6
@pytest.mark.slow
def test_pw6_oauth2_proxy_role_restriction(
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

    _ensure_role(headers, "MANAGER")
    _assign_role_to_user_api(headers, TEST_USER, "MANAGER")
    _ensure_user(
        headers,
        "unauth_user",
        "UnauthPass1!",
        email="unauth@example.com",
        first_name="Unauth",
        last_name="User",
    )

    workspace = workspace_factory("pw6-oauth2-proxy-roles", "pw6_oauth2_proxy_compose")
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
    workspace_manager.replace(
        workspace,
        "docker-compose.yml",
        '    #OAUTH2_PROXY_ALLOWED_ROLES: "MANAGER"',
        '    OAUTH2_PROXY_ALLOWED_ROLES: "MANAGER"',
    )

    process_manager.start_secret_webapp(workspace)
    workspace_stack = DockerStack(workspace)
    workspace_stack.rm("oauth2-proxy")
    workspace_stack.up_no_deps("oauth2-proxy")
    try:
        protected_url = "http://localhost:4180/secret/index.html"
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            try:
                candidate = requests.get(protected_url, timeout=5, allow_redirects=False)
                if candidate.status_code in (302, 303):
                    break
            except requests.RequestException:
                pass
            time.sleep(1)

        context1 = browser.new_context(ignore_https_errors=True)
        page1 = context1.new_page()
        page1.set_default_timeout(20_000)
        capture_page_artifacts(page1, "oauth2-proxy-role-denied")
        page1.goto(protected_url, wait_until="domcontentloaded")
        page1.get_by_role("textbox", name="Username or email").fill("unauth_user")
        page1.get_by_role("textbox", name="Password").fill("UnauthPass1!")
        page1.get_by_role("button", name="Sign In").click()
        page1.wait_for_load_state("networkidle")
        denied_content = page1.content().lower()
        assert (
            "403" in denied_content
            or "forbidden" in denied_content
            or "you do not have access" in denied_content
            or "unauthorized" in denied_content
        ), f"User without MANAGER role should be denied access, got: {page1.url}"
        context1.close()

        context2 = browser.new_context(ignore_https_errors=True)
        page2 = context2.new_page()
        page2.set_default_timeout(20_000)
        capture_page_artifacts(page2, "oauth2-proxy-role-allowed")
        page2.goto(protected_url, wait_until="domcontentloaded")
        page2.get_by_role("textbox", name="Username or email").fill(TEST_USER)
        page2.get_by_role("textbox", name="Password").fill(TEST_PASSWORD)
        page2.get_by_role("button", name="Sign In").click()
        page2.wait_for_load_state("networkidle")
        assert page2.get_by_role("heading", name="Keycloak rocks !").count() == 1, (
            "User with MANAGER role should be granted access through oauth2-proxy"
        )
        context2.close()
    finally:
        workspace_stack.rm("oauth2-proxy")

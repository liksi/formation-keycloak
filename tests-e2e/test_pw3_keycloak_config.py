from __future__ import annotations

import pytest
import requests

from conftest import (KEYCLOAK_URL, MAILDEV_URL, REALM_NAME,
                      SECRET_WEBAPP_CLIENT, TEST_PASSWORD, TEST_USER,
                      _add_required_action_api, _add_user_to_group_api,
                      _admin_headers, _assign_role_to_group_api,
                      _client_secret, _configure_smtp_api,
                      _ensure_client_scope_assigned, _ensure_group,
                      _ensure_role, _ensure_user,
                      _ensure_user_profile_attribute, _set_password_policy_api,
                      _set_user_attribute_api, _trigger_actions_email_api,
                      _update_client)
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

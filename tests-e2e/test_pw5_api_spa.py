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

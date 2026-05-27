from __future__ import annotations

import pytest

from conftest import CURL_CLIENT, TEST_PASSWORD, TEST_USER
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

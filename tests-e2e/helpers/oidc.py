from __future__ import annotations

import jwt as pyjwt
import requests


def get_openid_configuration(issuer_url: str) -> dict:
    url = f"{issuer_url.rstrip('/')}/.well-known/openid-configuration"
    r = requests.get(url, timeout=10)
    assert r.status_code == 200, f"OIDC discovery failed: {r.status_code} {r.text}"
    return r.json()


def get_token(
    issuer_url: str,
    client_id: str,
    username: str,
    password: str,
    client_secret: str | None = None,
    scope: str | None = None,
) -> dict:
    token_url = get_openid_configuration(issuer_url)["token_endpoint"]
    data: dict = {
        "grant_type": "password",
        "client_id": client_id,
        "username": username,
        "password": password,
    }
    if client_secret:
        data["client_secret"] = client_secret
    if scope:
        data["scope"] = scope
    r = requests.post(token_url, data=data, timeout=30)
    assert r.status_code == 200, f"Token generation failed: {r.status_code} {r.text}"
    return r.json()


def refresh_token(
    issuer_url: str,
    client_id: str,
    refresh_token_str: str,
    client_secret: str | None = None,
) -> dict:
    token_url = get_openid_configuration(issuer_url)["token_endpoint"]
    data: dict = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token_str,
    }
    if client_secret:
        data["client_secret"] = client_secret
    r = requests.post(token_url, data=data, timeout=30)
    assert r.status_code == 200, f"Token refresh failed: {r.status_code} {r.text}"
    return r.json()


def userinfo(issuer_url: str, access_token: str) -> requests.Response:
    userinfo_url = get_openid_configuration(issuer_url)["userinfo_endpoint"]
    return requests.get(
        userinfo_url,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )


def decode_jwt(token: str) -> dict:
    return pyjwt.decode(token, options={"verify_signature": False}, leeway=10)

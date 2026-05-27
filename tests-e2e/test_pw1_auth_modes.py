from __future__ import annotations

import pytest
import requests


@pytest.mark.pw1
def test_pw1_none_mode_allows_direct_secret_access(workspace_factory, process_manager):
    workspace = workspace_factory("pw1-none")
    process_manager.start_secret_webapp(workspace)

    home = requests.get("http://localhost:8090/", timeout=20)
    secret = requests.get(
        "http://localhost:8090/secret/index.html", timeout=20, allow_redirects=False
    )

    assert home.status_code == 200
    assert secret.status_code == 200
    assert "Keycloak rocks" in secret.text


@pytest.mark.pw1
def test_pw1_basic_mode_requires_basic_auth(workspace_factory, process_manager):
    workspace = workspace_factory("pw1-basic", "pw1_basic")
    process_manager.start_secret_webapp(workspace)

    unauthenticated = requests.get(
        "http://localhost:8090/secret/index.html",
        timeout=20,
        allow_redirects=False,
    )
    authenticated = requests.get(
        "http://localhost:8090/secret/index.html",
        auth=("user", "pwd"),
        timeout=20,
    )

    assert unauthenticated.status_code == 401
    assert "Basic" in unauthenticated.headers["WWW-Authenticate"]
    assert authenticated.status_code == 200
    assert "Keycloak rocks" in authenticated.text


@pytest.mark.pw1
def test_pw1_form_mode_uses_session_cookie(workspace_factory, process_manager):
    workspace = workspace_factory("pw1-form", "pw1_form")
    process_manager.start_secret_webapp(workspace)

    session = requests.Session()
    redirected = session.get(
        "http://localhost:8090/secret/index.html",
        timeout=20,
        allow_redirects=False,
    )
    login = session.post(
        "http://localhost:8090/login",
        data={"username": "user", "password": "pwd"},
        timeout=20,
        allow_redirects=False,
    )
    cookie_value = session.cookies.get("JSESSIONID")
    authenticated = session.get("http://localhost:8090/secret/index.html", timeout=20)

    assert redirected.status_code in (302, 303)
    assert cookie_value
    assert login.status_code in (302, 303)
    assert authenticated.status_code == 200
    assert "Keycloak rocks" in authenticated.text


@pytest.mark.pw1
def test_pw1_form_mode_cookie_httponly(workspace_factory, process_manager):
    workspace = workspace_factory("pw1-form-httponly", "pw1_form")
    process_manager.start_secret_webapp(workspace)

    session = requests.Session()
    initial = session.get(
        "http://localhost:8090/secret/index.html",
        timeout=20,
        allow_redirects=False,
    )
    login = session.post(
        "http://localhost:8090/login",
        data={"username": "user", "password": "pwd"},
        timeout=20,
        allow_redirects=False,
    )

    combined_cookies = " ".join(filter(None, [
        initial.headers.get("Set-Cookie", ""),
        login.headers.get("Set-Cookie", ""),
    ]))
    assert "JSESSIONID" in combined_cookies
    assert "HttpOnly" in combined_cookies


@pytest.mark.pw1
def test_pw1_form_mode_session_invalidated_after_restart(workspace_factory, process_manager):
    workspace = workspace_factory("pw1-form-restart", "pw1_form")
    process_manager.start_secret_webapp(workspace)

    session = requests.Session()
    session.get(
        "http://localhost:8090/secret/index.html",
        timeout=20,
        allow_redirects=False,
    )
    session.post(
        "http://localhost:8090/login",
        data={"username": "user", "password": "pwd"},
        timeout=20,
    )
    cookie_value = session.cookies.get("JSESSIONID")
    assert cookie_value, "Expected a session cookie after login"

    before_restart = requests.get(
        "http://localhost:8090/secret/index.html",
        cookies={"JSESSIONID": cookie_value},
        timeout=20,
        allow_redirects=False,
    )
    assert before_restart.status_code == 200, "Cookie should be valid before restart"

    process_manager.stop_all()
    process_manager.start_secret_webapp(workspace)

    after_restart = requests.get(
        "http://localhost:8090/secret/index.html",
        cookies={"JSESSIONID": cookie_value},
        timeout=20,
        allow_redirects=False,
    )
    assert after_restart.status_code in (302, 303), (
        "Stale session cookie should trigger redirect to login after server restart"
    )

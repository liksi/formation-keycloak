from __future__ import annotations

import subprocess
import time

import pytest
import requests

from helpers.oidc import decode_jwt


# --- PW7 helpers (use PW7 KC on port 18080, NOT the main KC on 8080) ---

def _pw7_admin_headers(base_url: str) -> dict:
    resp = requests.post(
        f"{base_url}/realms/master/protocol/openid-connect/token",
        data={
            "client_id": "admin-cli",
            "username": "admin",
            "password": "admin",
            "grant_type": "password",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return {
        "Authorization": f"Bearer {resp.json()['access_token']}",
        "Content-Type": "application/json",
    }


def _pw7_client_uuid(base_url: str, headers: dict, realm: str, client_id: str) -> str | None:
    resp = requests.get(
        f"{base_url}/admin/realms/{realm}/clients",
        headers=headers,
        params={"clientId": client_id},
        timeout=30,
    )
    resp.raise_for_status()
    clients = resp.json()
    return clients[0]["id"] if clients else None


def _pw7_ensure_client(
    base_url: str, headers: dict, realm: str, client_id: str, *, direct_access: bool = False
) -> None:
    payload = {
        "clientId": client_id,
        "enabled": True,
        "publicClient": True,
        "directAccessGrantsEnabled": direct_access,
        "standardFlowEnabled": True,
        "redirectUris": ["http://localhost:9999/*"],
    }
    existing_id = _pw7_client_uuid(base_url, headers, realm, client_id)
    if existing_id is None:
        requests.post(
            f"{base_url}/admin/realms/{realm}/clients",
            headers=headers,
            json=payload,
            timeout=30,
        ).raise_for_status()
    else:
        requests.put(
            f"{base_url}/admin/realms/{realm}/clients/{existing_id}",
            headers=headers,
            json=payload,
            timeout=30,
        ).raise_for_status()


def _pw7_user_id(base_url: str, headers: dict, realm: str, username: str) -> str | None:
    resp = requests.get(
        f"{base_url}/admin/realms/{realm}/users",
        headers=headers,
        params={"username": username},
        timeout=30,
    )
    resp.raise_for_status()
    users = [u for u in resp.json() if u["username"] == username]
    return users[0]["id"] if users else None


def _pw7_ensure_user(
    base_url: str,
    headers: dict,
    realm: str,
    username: str,
    password: str,
    *,
    age: str | None = None,
) -> None:
    payload: dict = {
        "username": username,
        "enabled": True,
        "email": f"{username}@pw7.test",
        "firstName": username,
        "lastName": "Test",
    }
    if age:
        payload["attributes"] = {"age": [age]}
    user_id = _pw7_user_id(base_url, headers, realm, username)
    if user_id is None:
        requests.post(
            f"{base_url}/admin/realms/{realm}/users",
            headers=headers,
            json=payload,
            timeout=30,
        ).raise_for_status()
        user_id = _pw7_user_id(base_url, headers, realm, username)
    else:
        existing_resp = requests.get(
            f"{base_url}/admin/realms/{realm}/users/{user_id}",
            headers=headers,
            timeout=30,
        )
        existing_resp.raise_for_status()
        existing = existing_resp.json()
        existing.update(payload)
        requests.put(
            f"{base_url}/admin/realms/{realm}/users/{user_id}",
            headers=headers,
            json=existing,
            timeout=30,
        ).raise_for_status()
    requests.put(
        f"{base_url}/admin/realms/{realm}/users/{user_id}/reset-password",
        headers=headers,
        json={"type": "password", "value": password, "temporary": False},
        timeout=30,
    ).raise_for_status()


def _pw7_set_user_attribute(
    base_url: str, headers: dict, realm: str, username: str, key: str, value: str
) -> None:
    user_id = _pw7_user_id(base_url, headers, realm, username)
    assert user_id, f"PW7 user {username} not found"
    resp = requests.get(
        f"{base_url}/admin/realms/{realm}/users/{user_id}", headers=headers, timeout=30
    )
    resp.raise_for_status()
    payload = resp.json()
    attrs = payload.get("attributes", {})
    attrs[key] = [value]
    payload["attributes"] = attrs
    requests.put(
        f"{base_url}/admin/realms/{realm}/users/{user_id}",
        headers=headers,
        json=payload,
        timeout=30,
    ).raise_for_status()


def _pw7_add_required_action(
    base_url: str, headers: dict, realm: str, username: str, action: str
) -> None:
    user_id = _pw7_user_id(base_url, headers, realm, username)
    assert user_id, f"PW7 user {username} not found"
    resp = requests.get(
        f"{base_url}/admin/realms/{realm}/users/{user_id}", headers=headers, timeout=30
    )
    resp.raise_for_status()
    payload = resp.json()
    actions = set(payload.get("requiredActions", []))
    actions.add(action)
    payload["requiredActions"] = sorted(actions)
    requests.put(
        f"{base_url}/admin/realms/{realm}/users/{user_id}",
        headers=headers,
        json=payload,
        timeout=30,
    ).raise_for_status()


def _pw7_register_required_action(
    base_url: str, headers: dict, realm: str, action_id: str
) -> None:
    actions_resp = requests.get(
        f"{base_url}/admin/realms/{realm}/authentication/required-actions",
        headers=headers,
        timeout=30,
    )
    actions_resp.raise_for_status()
    if any(a["alias"] == action_id for a in actions_resp.json()):
        return
    unregistered_resp = requests.get(
        f"{base_url}/admin/realms/{realm}/authentication/unregistered-required-actions",
        headers=headers,
        timeout=30,
    )
    if unregistered_resp.ok:
        action = next(
            (a for a in unregistered_resp.json() if a["providerId"] == action_id), None
        )
        if action:
            requests.post(
                f"{base_url}/admin/realms/{realm}/authentication/register-required-action",
                headers=headers,
                json={"providerId": action_id, "name": action.get("name", action_id)},
                timeout=30,
            ).raise_for_status()


def _pw7_setup_question_auth_flow(
    base_url: str, headers: dict, realm: str, flow_alias: str
) -> None:
    flows_resp = requests.get(
        f"{base_url}/admin/realms/{realm}/authentication/flows",
        headers=headers,
        timeout=30,
    )
    flows_resp.raise_for_status()
    if not any(f["alias"] == flow_alias for f in flows_resp.json()):
        requests.post(
            f"{base_url}/admin/realms/{realm}/authentication/flows/browser/copy",
            headers=headers,
            json={"newName": flow_alias},
            timeout=30,
        ).raise_for_status()

        requests.post(
            f"{base_url}/admin/realms/{realm}/authentication/flows/{flow_alias}/executions/execution",
            headers=headers,
            json={"provider": "secret-question-authenticator"},
            timeout=30,
        ).raise_for_status()

        executions_resp = requests.get(
            f"{base_url}/admin/realms/{realm}/authentication/flows/{flow_alias}/executions",
            headers=headers,
            timeout=30,
        )
        executions_resp.raise_for_status()
        new_exec = next(
            (
                e
                for e in executions_resp.json()
                if e.get("providerId") == "secret-question-authenticator"
            ),
            None,
        )
        if new_exec:
            new_exec["requirement"] = "REQUIRED"
            requests.put(
                f"{base_url}/admin/realms/{realm}/authentication/flows/{flow_alias}/executions",
                headers=headers,
                json=new_exec,
                timeout=30,
            ).raise_for_status()

    realm_resp = requests.get(
        f"{base_url}/admin/realms/{realm}", headers=headers, timeout=30
    )
    realm_resp.raise_for_status()
    realm_payload = realm_resp.json()
    realm_payload["browserFlow"] = flow_alias
    requests.put(
        f"{base_url}/admin/realms/{realm}", headers=headers, json=realm_payload, timeout=30
    ).raise_for_status()


def _pw7_reset_browser_flow(base_url: str, headers: dict, realm: str) -> None:
    realm_resp = requests.get(
        f"{base_url}/admin/realms/{realm}", headers=headers, timeout=30
    )
    realm_resp.raise_for_status()
    payload = realm_resp.json()
    payload["browserFlow"] = "browser"
    requests.put(
        f"{base_url}/admin/realms/{realm}", headers=headers, json=payload, timeout=30
    ).raise_for_status()


# --- Fixtures ---


@pytest.fixture(scope="module")
def pw7_keycloak(workspace_manager):
    """Start a dedicated KC instance with patched provider + theme on port 18080."""
    workspace = workspace_manager.create("pw7-kc-full")
    for solution in (
        "pw7_theme_enable",
        "pw7_age_mapper",
        "pw7_required_action",
        "pw7_question_authenticator",
    ):
        workspace_manager.apply_solution(workspace, solution)

    subprocess.run(
        ["./mvnw", "package", "-q", "-DskipTests"],
        cwd=workspace / "keycloak/provider",
        check=True,
    )

    jar = workspace / "keycloak/provider/target/registration-spi-1.0.0-SNAPSHOT.jar"
    theme_dir = workspace / "keycloak/theme"
    container = "keycloak-pw7-test"

    subprocess.run(["docker", "rm", "-f", container], capture_output=True)
    subprocess.run(
        [
            "docker", "run", "-d", "--name", container,
            "-p", "18080:8080",
            "-e", "KEYCLOAK_ADMIN=admin",
            "-e", "KEYCLOAK_ADMIN_PASSWORD=admin",
            "-v", f"{jar}:/opt/keycloak/providers/registration-spi.jar",
            "-v", f"{theme_dir}/:/opt/keycloak/themes/",
            "quay.io/keycloak/keycloak:26.6.2",
            "start-dev",
        ],
        check=True,
    )

    base_url = "http://localhost:18080"
    for _ in range(60):
        try:
            if requests.get(f"{base_url}/health/ready", timeout=3).status_code == 200:
                break
        except Exception:
            pass
        time.sleep(2)
    else:
        subprocess.run(["docker", "rm", "-f", container], capture_output=True)
        pytest.fail("PW7 Keycloak instance failed to start in 120s")

    headers = _pw7_admin_headers(base_url)
    realm_resp = requests.get(
        f"{base_url}/admin/realms/master", headers=headers, timeout=30
    )
    realm_resp.raise_for_status()
    realm_payload = realm_resp.json()
    realm_payload["sslRequired"] = "NONE"
    requests.put(
        f"{base_url}/admin/realms/master", headers=headers, json=realm_payload, timeout=30
    ).raise_for_status()

    yield {"base_url": base_url, "workspace": workspace}

    subprocess.run(["docker", "rm", "-f", container], capture_output=True)


# --- Tests ---


@pytest.mark.pw7
def test_pw7_theme_solution_patch_applies(workspace_factory):
    workspace = workspace_factory("pw7-theme", "pw7_theme_enable")
    content = (
        workspace / "keycloak/theme/custom/login/messages/messages_en.properties"
    ).read_text(encoding="utf-8")
    dockerfile = (workspace / "keycloak/Dockerfile").read_text(encoding="utf-8")

    assert "Dear user, please login to access this page" in content
    assert "COPY theme/ /opt/keycloak/themes/" in dockerfile


@pytest.mark.pw7
def test_pw7_provider_solution_patches_apply(workspace_factory):
    workspace = workspace_factory(
        "pw7-provider",
        "pw7_age_mapper",
        "pw7_required_action",
        "pw7_question_authenticator",
    )
    age_mapper = (
        workspace
        / "keycloak/provider/src/main/java/fr/liksi/formation/keycloak/mapper/AgeMapper.java"
    ).read_text(encoding="utf-8")
    required_action = (
        workspace
        / "keycloak/provider/src/main/java/fr/liksi/formation/keycloak/requiredaction/UpdateQuestionAction.java"
    ).read_text(encoding="utf-8")
    authenticator = (
        workspace
        / "keycloak/provider/src/main/java/fr/liksi/formation/keycloak/authenticator/QuestionAuthenticator.java"
    ).read_text(encoding="utf-8")

    assert 'getFirstAttribute("age")' in age_mapper
    assert 'setSingleAttribute("question", question)' in required_action
    assert "equalsIgnoreCase" in authenticator


@pytest.mark.pw7
@pytest.mark.slow
def test_pw7_login_page_shows_custom_title(pw7_keycloak, browser):
    base_url = pw7_keycloak["base_url"]
    headers = _pw7_admin_headers(base_url)

    realm_resp = requests.get(
        f"{base_url}/admin/realms/master", headers=headers, timeout=30
    )
    realm_resp.raise_for_status()
    realm_payload = realm_resp.json()
    realm_payload["loginTheme"] = "custom"
    requests.put(
        f"{base_url}/admin/realms/master", headers=headers, json=realm_payload, timeout=30
    ).raise_for_status()

    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    page.set_default_timeout(20_000)
    try:
        page.goto(
            f"{base_url}/realms/master/protocol/openid-connect/auth"
            f"?client_id=security-admin-console&response_type=code&scope=openid"
            f"&redirect_uri={base_url}/admin/master/console/",
            wait_until="domcontentloaded",
        )
        page.wait_for_load_state("networkidle")

        assert "Dear user, please login to access this page" in page.content(), (
            "Custom theme should display the custom loginAccountTitle message on the login page"
        )
    finally:
        context.close()


@pytest.mark.pw7
@pytest.mark.slow
def test_pw7_age_mapper_adult_claim(pw7_keycloak):
    base_url = pw7_keycloak["base_url"]
    headers = _pw7_admin_headers(base_url)
    realm = "master"

    _pw7_ensure_client(base_url, headers, realm, "pw7-test-client", direct_access=True)
    client_uuid = _pw7_client_uuid(base_url, headers, realm, "pw7-test-client")

    mappers_resp = requests.get(
        f"{base_url}/admin/realms/{realm}/clients/{client_uuid}/protocol-mappers/models",
        headers=headers,
        timeout=30,
    )
    mappers_resp.raise_for_status()
    if not any(m.get("protocolMapper") == "AGE_MAPPER" for m in mappers_resp.json()):
        requests.post(
            f"{base_url}/admin/realms/{realm}/clients/{client_uuid}/protocol-mappers/models",
            headers=headers,
            json={
                "name": "age-mapper",
                "protocol": "openid-connect",
                "protocolMapper": "AGE_MAPPER",
                "consentRequired": False,
                "config": {
                    "id.token.claim": "true",
                    "access.token.claim": "true",
                    "userinfo.token.claim": "true",
                },
            },
            timeout=30,
        ).raise_for_status()

    # AgeMapper.MIN_AGE = 21; use age=25 for adult, age=15 for minor
    _pw7_ensure_user(base_url, headers, realm, "adult_user", "AdultPass1!", age="25")
    _pw7_ensure_user(base_url, headers, realm, "minor_user", "MinorPass1!", age="15")

    adult_resp = requests.post(
        f"{base_url}/realms/{realm}/protocol/openid-connect/token",
        data={
            "client_id": "pw7-test-client",
            "username": "adult_user",
            "password": "AdultPass1!",
            "grant_type": "password",
        },
        timeout=30,
    )
    adult_resp.raise_for_status()
    minor_resp = requests.post(
        f"{base_url}/realms/{realm}/protocol/openid-connect/token",
        data={
            "client_id": "pw7-test-client",
            "username": "minor_user",
            "password": "MinorPass1!",
            "grant_type": "password",
        },
        timeout=30,
    )
    minor_resp.raise_for_status()

    adult_claims = decode_jwt(adult_resp.json()["access_token"])
    minor_claims = decode_jwt(minor_resp.json()["access_token"])

    assert adult_claims.get("is_adult") is True, (
        f"User with age=25 should have is_adult=true, got: {adult_claims.get('is_adult')!r}"
    )
    assert minor_claims.get("is_adult") is False, (
        f"User with age=15 should have is_adult=false, got: {minor_claims.get('is_adult')!r}"
    )


@pytest.mark.pw7
@pytest.mark.slow
def test_pw7_required_action_question_form(pw7_keycloak, browser, capture_page_artifacts):
    base_url = pw7_keycloak["base_url"]
    headers = _pw7_admin_headers(base_url)
    realm = "master"

    _pw7_ensure_client(base_url, headers, realm, "pw7-test-client", direct_access=True)
    _pw7_register_required_action(base_url, headers, realm, "update_question")
    _pw7_ensure_user(base_url, headers, realm, "question_user", "QuestionPass1!")
    _pw7_add_required_action(base_url, headers, realm, "question_user", "update_question")

    auth_url = (
        f"{base_url}/realms/{realm}/protocol/openid-connect/auth"
        "?client_id=pw7-test-client&response_type=code&scope=openid"
        "&redirect_uri=http://localhost:9999/"
    )

    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    page.set_default_timeout(20_000)
    capture_page_artifacts(page, "pw7-required-action")
    try:
        page.goto(auth_url, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.get_by_role("textbox", name="Username or email").fill("question_user")
        page.get_by_role("textbox", name="Password").fill("QuestionPass1!")
        page.get_by_role("button", name="Sign In").click()
        page.wait_for_load_state("networkidle")

        assert "localhost:9999" not in page.url, (
            "Required action should intercept the flow before redirect to client"
        )
        page_content = page.content().lower()
        assert "question" in page_content or "answer" in page_content, (
            "KC should show the Update Question form for users with update_question required action"
        )

        page.fill('[name="question"]', "What is my favorite color?")
        page.fill('[name="answer"]', "blue")
        try:
            with page.expect_navigation(wait_until="commit", timeout=8_000):
                page.locator('input[type="submit"], button[type="submit"]').first.click()
        except Exception:
            pass

        assert "localhost:9999" in page.url or "code=" in page.url, (
            "After completing the Update Question required action, KC should redirect to the client"
        )
    finally:
        context.close()


@pytest.mark.pw7
@pytest.mark.slow
def test_pw7_question_authenticator_flow(pw7_keycloak, browser, capture_page_artifacts):
    base_url = pw7_keycloak["base_url"]
    headers = _pw7_admin_headers(base_url)
    realm = "master"

    _pw7_ensure_client(base_url, headers, realm, "pw7-test-client", direct_access=True)
    _pw7_setup_question_auth_flow(base_url, headers, realm, "browser-question")
    _pw7_ensure_user(base_url, headers, realm, "auth_question_user", "AuthQPass1!")
    _pw7_set_user_attribute(
        base_url, headers, realm, "auth_question_user", "question", "What is 2+2?"
    )
    _pw7_set_user_attribute(base_url, headers, realm, "auth_question_user", "answer", "4")

    auth_url = (
        f"{base_url}/realms/{realm}/protocol/openid-connect/auth"
        "?client_id=pw7-test-client&response_type=code&scope=openid"
        "&redirect_uri=http://localhost:9999/"
    )

    context1 = browser.new_context(ignore_https_errors=True)
    page1 = context1.new_page()
    page1.set_default_timeout(20_000)
    capture_page_artifacts(page1, "pw7-question-correct")
    try:
        page1.goto(auth_url, wait_until="domcontentloaded")
        page1.wait_for_load_state("networkidle")
        page1.get_by_role("textbox", name="Username or email").fill("auth_question_user")
        page1.get_by_role("textbox", name="Password").fill("AuthQPass1!")
        page1.get_by_role("button", name="Sign In").click()
        page1.wait_for_load_state("networkidle")

        assert any(
            word in page1.content().lower() for word in ["question", "answer"]
        ), "Question authenticator should present the question form after credentials"

        page1.fill('[name="answer"]', "4")
        try:
            with page1.expect_navigation(wait_until="commit", timeout=8_000):
                page1.locator('input[type="submit"], button[type="submit"]').first.click()
        except Exception:
            pass

        assert "localhost:9999" in page1.url, (
            "Correct answer should complete the authentication and redirect to the client"
        )
    finally:
        context1.close()

    context2 = browser.new_context(ignore_https_errors=True)
    page2 = context2.new_page()
    page2.set_default_timeout(20_000)
    capture_page_artifacts(page2, "pw7-question-wrong")
    try:
        page2.goto(auth_url, wait_until="domcontentloaded")
        page2.wait_for_load_state("networkidle")
        page2.get_by_role("textbox", name="Username or email").fill("auth_question_user")
        page2.get_by_role("textbox", name="Password").fill("AuthQPass1!")
        page2.get_by_role("button", name="Sign In").click()
        page2.wait_for_load_state("networkidle")

        page2.fill('[name="answer"]', "wrong_answer")
        page2.locator('input[type="submit"], button[type="submit"]').first.click()
        page2.wait_for_load_state("networkidle")

        assert "localhost:9999" not in page2.url, (
            "Wrong answer should keep the user on the KC authentication page"
        )
        assert any(
            word in page2.content().lower()
            for word in ["wrong", "error", "invalid", "incorrect"]
        ), "KC should display an error message for a wrong answer"
    finally:
        context2.close()
        _pw7_reset_browser_flow(base_url, headers, realm)

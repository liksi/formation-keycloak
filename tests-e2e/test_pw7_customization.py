from __future__ import annotations

import contextlib
import http.server
import socketserver
import subprocess
import threading
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
    base_url: str,
    headers: dict,
    realm: str,
    client_id: str,
    *,
    direct_access: bool = False,
    redirect_uris: list[str] | None = None,
) -> None:
    payload = {
        "clientId": client_id,
        "enabled": True,
        "publicClient": True,
        "directAccessGrantsEnabled": direct_access,
        "standardFlowEnabled": True,
        "redirectUris": redirect_uris or ["http://localhost:9999/*"],
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
        "requiredActions": [],
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


def _pw7_clear_required_actions(
    base_url: str, headers: dict, realm: str, username: str
) -> None:
    user_id = _pw7_user_id(base_url, headers, realm, username)
    if not user_id:
        return
    resp = requests.get(
        f"{base_url}/admin/realms/{realm}/users/{user_id}", headers=headers, timeout=30
    )
    resp.raise_for_status()
    payload = resp.json()
    if not payload.get("requiredActions"):
        return
    payload["requiredActions"] = []
    requests.put(
        f"{base_url}/admin/realms/{realm}/users/{user_id}",
        headers=headers,
        json=payload,
        timeout=30,
    ).raise_for_status()


def _pw7_register_required_action(
    base_url: str, headers: dict, realm: str, action_id: str
) -> None:
    # Even if the SPI JAR is deployed, KC does not automatically register a required
    # action in a realm. It must be registered explicitly via the Admin API before it
    # can be assigned to users. The unregistered-required-actions endpoint discovers
    # available but not-yet-registered actions from loaded SPIs.
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
    # KC does not allow adding an authenticator directly to a top-level browser flow:
    # it must be nested inside a sub-flow of "forms" (the credential-gathering group).
    # Strategy: copy the browser flow → add a sub-flow inside "forms" → add the
    # secret-question-authenticator inside that sub-flow → set both to REQUIRED →
    # move the sub-flow to index 1 (right after Username/Password) via raise-priority.
    # The outer sub-flow is set as browser flow on the realm.
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
    executions_resp = requests.get(
        f"{base_url}/admin/realms/{realm}/authentication/flows/{flow_alias}/executions",
        headers=headers,
        timeout=30,
    )
    executions_resp.raise_for_status()
    forms_alias = f"{flow_alias} forms"
    question_subflow_alias = f"{flow_alias} question challenge"
    existing_exec = next(
        (
            e
            for e in executions_resp.json()
            if e.get("providerId") == "secret-question-authenticator"
        ),
        None,
    )
    if existing_exec is None:
        requests.post(
            f"{base_url}/admin/realms/{realm}/authentication/flows/{forms_alias}/executions/flow",
            headers=headers,
            json={
                "alias": question_subflow_alias,
                "type": "basic-flow",
                "provider": "basic-flow",
                "description": "Secret question challenge",
            },
            timeout=30,
        ).raise_for_status()
        requests.post(
            f"{base_url}/admin/realms/{realm}/authentication/flows/{question_subflow_alias}/executions/execution",
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
    question_subflow_exec = next(
        (e for e in executions_resp.json() if e.get("displayName") == question_subflow_alias),
        None,
    )
    if question_subflow_exec:
        question_subflow_exec["requirement"] = "REQUIRED"
        requests.put(
            f"{base_url}/admin/realms/{realm}/authentication/flows/{flow_alias}/executions",
            headers=headers,
            json=question_subflow_exec,
            timeout=30,
        ).raise_for_status()
        while question_subflow_exec.get("index", 99) > 1:
            requests.post(
                f"{base_url}/admin/realms/{realm}/authentication/executions/{question_subflow_exec['id']}/raise-priority",
                headers=headers,
                timeout=30,
            ).raise_for_status()
            executions_resp = requests.get(
                f"{base_url}/admin/realms/{realm}/authentication/flows/{flow_alias}/executions",
                headers=headers,
                timeout=30,
            )
            executions_resp.raise_for_status()
            question_subflow_exec = next(
                (e for e in executions_resp.json() if e.get("displayName") == question_subflow_alias),
                question_subflow_exec,
            )

    question_execs = requests.get(
        f"{base_url}/admin/realms/{realm}/authentication/flows/{question_subflow_alias}/executions",
        headers=headers,
        timeout=30,
    )
    question_execs.raise_for_status()
    existing_exec = next(
        (
            e
            for e in question_execs.json()
            if e.get("providerId") == "secret-question-authenticator"
        ),
        None,
    )
    if existing_exec:
        existing_exec["requirement"] = "REQUIRED"
        requests.put(
            f"{base_url}/admin/realms/{realm}/authentication/flows/{question_subflow_alias}/executions",
            headers=headers,
            json=existing_exec,
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


def _pw7_fill_login_form(page, username: str, password: str) -> None:
    # Use attribute selectors rather than get_by_role("textbox", name="Username or email")
    # because the custom theme may change the visible label text.
    page.locator('input[name="username"], input#username').first.fill(username)
    page.locator('input[name="password"], input#password').first.fill(password)
    page.locator('input[type="submit"], button[type="submit"], input[name="login"]').first.click()


def _pw7_enable_unmanaged_attributes(base_url: str, headers: dict, realm: str) -> None:
    # KC 26 introduced User Profile by default: only attributes declared in the schema
    # are accepted; everything else is silently dropped on user PUT.
    # Setting unmanagedAttributePolicy=ENABLED allows arbitrary custom attributes
    # (age, question, answer) without declaring each one individually.
    config_resp = requests.get(
        f"{base_url}/admin/realms/{realm}/users/profile",
        headers=headers,
        timeout=30,
    )
    if config_resp.status_code == 404:
        return
    config_resp.raise_for_status()
    config = config_resp.json() or {}
    config["unmanagedAttributePolicy"] = "ENABLED"
    requests.put(
        f"{base_url}/admin/realms/{realm}/users/profile",
        headers=headers,
        json=config,
        timeout=30,
    ).raise_for_status()


# Playwright throws "connection refused" when KC redirects to a redirect_uri with no server
# listening. We spin up a minimal in-process HTTP server to catch those redirects,
# which lets us assert that the authorization code was delivered correctly.
# The server uses port 0 (OS-assigned) to avoid conflicts between concurrent tests.
class _PW7CallbackHandler(http.server.BaseHTTPRequestHandler):
    callback_path: str | None = None

    def do_GET(self):
        type(self).callback_path = self.path
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<html><body>PW7 callback received</body></html>")

    def log_message(self, format, *args):
        return


class _PW7ReusableTCPServer(socketserver.TCPServer):
    # Prevents "Address already in use" if the previous test released the port
    # just moments before (TIME_WAIT TCP state).
    allow_reuse_address = True


@contextlib.contextmanager
def _pw7_callback_server():
    _PW7CallbackHandler.callback_path = None
    with _PW7ReusableTCPServer(("127.0.0.1", 0), _PW7CallbackHandler) as server:
        server.timeout = 0.5
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield server.server_address[1]
        finally:
            server.shutdown()
            thread.join(timeout=2)


# --- Fixtures ---


@pytest.fixture(scope="module")
def pw7_keycloak(workspace_manager):
    """Start a dedicated KC instance with patched provider + theme on port 18080.

    Uses workspace_manager (session-scoped) directly instead of workspace_factory
    (function-scoped) because pytest forbids a module-scoped fixture from depending
    on a function-scoped one.
    """
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
            "-e", "KC_BOOTSTRAP_ADMIN_USERNAME=admin",
            "-e", "KC_BOOTSTRAP_ADMIN_PASSWORD=admin",
            "-v", f"{jar}:/opt/keycloak/providers/registration-spi.jar",
            "-v", f"{theme_dir}/:/opt/keycloak/themes/",
            # Must use the official image: the project's custom keycloak:latest has
            # ENTRYPOINT ["kc.sh", "start"] and cannot accept "start-dev" as CMD.
            # The official image uses bare ENTRYPOINT ["kc.sh"] which allows it.
            "quay.io/keycloak/keycloak:26.6.2",
            "start-dev",
        ],
        check=True,
    )

    base_url = "http://localhost:18080"
    for _ in range(60):
        container_state = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Status}}", container],
            capture_output=True,
            text=True,
        )
        if container_state.returncode == 0 and container_state.stdout.strip() == "exited":
            logs = subprocess.run(
                ["docker", "logs", container], capture_output=True, text=True
            )
            subprocess.run(["docker", "rm", "-f", container], capture_output=True)
            pytest.fail(f"PW7 Keycloak container exited during startup:\n{logs.stderr or logs.stdout}")
        try:
            master = requests.get(f"{base_url}/realms/master/.well-known/openid-configuration", timeout=3)
            if master.status_code == 200:
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
    realm_payload["loginTheme"] = "custom"
    requests.put(
        f"{base_url}/admin/realms/master", headers=headers, json=realm_payload, timeout=30
    ).raise_for_status()
    # Allow arbitrary user attributes without declaring each one in the User Profile schema.
    _pw7_enable_unmanaged_attributes(base_url, headers, "master")
    # Pre-populate question/answer on the admin user so that if the question-authenticator
    # flow is accidentally left active (e.g. a test fails mid-cleanup), the admin can still
    # log in through the browser without being blocked by the security question challenge.
    _pw7_set_user_attribute(
        base_url, headers, "master", "admin", "question", "Admin bootstrap question"
    )
    _pw7_set_user_attribute(base_url, headers, "master", "admin", "answer", "admin")

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

    # Reset in case a previous test left a custom browser flow active. The password grant
    # used here bypasses the browser flow, but resetting keeps the realm in a clean state.
    _pw7_reset_browser_flow(base_url, headers, realm)
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
    # The fixture is module-scoped: users persist across tests. If a previous test run
    # left a required action on these users, the password grant would fail (KC rejects
    # direct grants for users with pending required actions). Clear them defensively.
    _pw7_clear_required_actions(base_url, headers, realm, "adult_user")
    _pw7_clear_required_actions(base_url, headers, realm, "minor_user")
    # question/answer needed so the question-authenticator (if active) doesn't block login.
    _pw7_set_user_attribute(base_url, headers, realm, "adult_user", "question", "Adult question")
    _pw7_set_user_attribute(base_url, headers, realm, "adult_user", "answer", "adult")
    _pw7_set_user_attribute(base_url, headers, realm, "minor_user", "question", "Minor question")
    _pw7_set_user_attribute(base_url, headers, realm, "minor_user", "answer", "minor")

    adult_resp = requests.post(
        f"{base_url}/realms/{realm}/protocol/openid-connect/token",
        data={
            "client_id": "pw7-test-client",
            "username": "adult_user",
            "password": "AdultPass1!",
            "grant_type": "password",
            "scope": "openid",
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
            "scope": "openid",
        },
        timeout=30,
    )
    minor_resp.raise_for_status()

    # Decode id_token, not access_token: AgeMapper maps to id.token.claim=true.
    # In KC 26 the access token may omit mapper claims that are not tied to a client scope.
    adult_claims = decode_jwt(adult_resp.json()["id_token"])
    minor_claims = decode_jwt(minor_resp.json()["id_token"])

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

    # Ensure no custom auth flow is active before this test: we need the standard browser
    # flow so that the required action prompt is reached after normal credential entry.
    _pw7_reset_browser_flow(base_url, headers, realm)
    with _pw7_callback_server() as callback_port:
        _pw7_ensure_client(
            base_url,
            headers,
            realm,
            "pw7-test-client",
            direct_access=True,
            redirect_uris=[f"http://localhost:{callback_port}/*"],
        )
        _pw7_register_required_action(base_url, headers, realm, "update_question")
        _pw7_ensure_user(base_url, headers, realm, "question_user", "QuestionPass1!")
        # Clear any leftover required actions from a previous run before adding update_question,
        # to avoid stacking actions that would produce an unexpected form order.
        _pw7_clear_required_actions(base_url, headers, realm, "question_user")
        _pw7_add_required_action(base_url, headers, realm, "question_user", "update_question")
        auth_url = (
            f"{base_url}/realms/{realm}/protocol/openid-connect/auth"
            "?client_id=pw7-test-client&response_type=code&scope=openid"
            f"&redirect_uri=http://localhost:{callback_port}/"
        )
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.set_default_timeout(20_000)
        capture_page_artifacts(page, "pw7-required-action")
        try:
            page.goto(auth_url, wait_until="domcontentloaded")
            page.wait_for_load_state("networkidle")
            _pw7_fill_login_form(page, "question_user", "QuestionPass1!")
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
            # expect_navigation can raise if the redirect arrives faster than the context
            # manager starts, or if the target URL's server closes the connection immediately.
            # suppress() lets us continue and let wait_for_url do the real assertion.
            with contextlib.suppress(Exception):
                with page.expect_navigation(wait_until="load", timeout=10_000):
                    page.locator('input[type="submit"], button[type="submit"]').first.click()

            page.wait_for_url(f"http://localhost:{callback_port}/**", timeout=10_000)
            assert f"localhost:{callback_port}" in page.url and "code=" in page.url, (
                "After completing the Update Question required action, KC should redirect to the client"
            )
            assert _PW7CallbackHandler.callback_path is not None
            assert "code=" in _PW7CallbackHandler.callback_path
        finally:
            context.close()


@pytest.mark.pw7
@pytest.mark.slow
def test_pw7_question_authenticator_flow(pw7_keycloak, browser, capture_page_artifacts):
    base_url = pw7_keycloak["base_url"]
    headers = _pw7_admin_headers(base_url)
    realm = "master"

    # Start from a clean browser flow; _pw7_setup_question_auth_flow will then install
    # the custom flow and set it as the active browser flow for the realm.
    _pw7_reset_browser_flow(base_url, headers, realm)
    with _pw7_callback_server() as callback_port:
        _pw7_ensure_client(
            base_url,
            headers,
            realm,
            "pw7-test-client",
            direct_access=True,
            redirect_uris=[f"http://localhost:{callback_port}/*"],
        )
        _pw7_setup_question_auth_flow(base_url, headers, realm, "browser-question")
        _pw7_ensure_user(base_url, headers, realm, "auth_question_user", "AuthQPass1!")
        # Clear required actions: if update_question is still set from the previous test,
        # the browser flow would show that form instead of the authenticator challenge.
        _pw7_clear_required_actions(base_url, headers, realm, "auth_question_user")
        _pw7_set_user_attribute(
            base_url, headers, realm, "auth_question_user", "question", "What is 2+2?"
        )
        _pw7_set_user_attribute(base_url, headers, realm, "auth_question_user", "answer", "4")
        auth_url = (
            f"{base_url}/realms/{realm}/protocol/openid-connect/auth"
            "?client_id=pw7-test-client&response_type=code&scope=openid"
            f"&redirect_uri=http://localhost:{callback_port}/"
        )
        context1 = browser.new_context(ignore_https_errors=True)
        page1 = context1.new_page()
        page1.set_default_timeout(20_000)
        capture_page_artifacts(page1, "pw7-question-correct")
        try:
            page1.goto(auth_url, wait_until="domcontentloaded")
            page1.wait_for_load_state("networkidle")
            _pw7_fill_login_form(page1, "auth_question_user", "AuthQPass1!")
            page1.wait_for_load_state("networkidle")

            assert any(
                word in page1.content().lower() for word in ["question", "answer"]
            ), "Question authenticator should present the question form after credentials"

            page1.fill('[name="answer"]', "4")
            # Same suppress pattern as the required-action test: the redirect to the
            # callback server may arrive before expect_navigation is fully set up.
            with contextlib.suppress(Exception):
                with page1.expect_navigation(wait_until="load", timeout=10_000):
                    page1.locator('input[type="submit"], button[type="submit"]').first.click()

            page1.wait_for_url(f"http://localhost:{callback_port}/**", timeout=10_000)
            assert f"localhost:{callback_port}" in page1.url and "code=" in page1.url, (
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
        _pw7_fill_login_form(page2, "auth_question_user", "AuthQPass1!")
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

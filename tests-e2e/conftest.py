from __future__ import annotations

import os
import shutil
import socket
from pathlib import Path

import pytest
import requests

from helpers.http_ import wait_for_http
from helpers.keycloak_ui import login_to_realm_console
from helpers.stack import DockerStack, ProcessManager
from helpers.workspace import WorkspaceManager

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TESTS_ROOT = Path(__file__).resolve().parent
ARTIFACTS_ROOT = TESTS_ROOT / "artifacts"

KEYCLOAK_URL = "http://localhost:8080"
KEYCLOAK_ADMIN_USER = "admin"
KEYCLOAK_ADMIN_PASS = "admin"
REALM_NAME = "training"
MAILDEV_URL = "http://localhost:1080"

SECRET_WEBAPP_CLIENT = "secret-webapp"
CURL_CLIENT = "curl"
VUE_CLIENT = "vue"
OAUTH2_PROXY_CLIENT = "oauth2-proxy"
TEST_USER = "test"
TEST_PASSWORD = "pwd"

WEBAPP_PORT = 8090
API_PORT = 8091
VUE_APP_PORT = 8070
OAUTH2_PROXY_PORT = 4180


def _assert_port_available(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if sock.connect_ex(("127.0.0.1", port)) == 0:
            raise RuntimeError(f"Port {port} is already in use before tests start")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--keep-workspaces",
        action="store_true",
        default=False,
        help="Keep disposable /tmp workspaces after tests complete.",
    )


def pytest_configure(config: pytest.Config) -> None:
    ARTIFACTS_ROOT.mkdir(exist_ok=True)


def _admin_token() -> str:
    response = requests.post(
        f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
        data={
            "client_id": "admin-cli",
            "username": KEYCLOAK_ADMIN_USER,
            "password": KEYCLOAK_ADMIN_PASS,
            "grant_type": "password",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _admin_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_admin_token()}",
        "Content-Type": "application/json",
    }


def _ensure_training_realm() -> None:
    token = _admin_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    existing = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if existing.status_code == 404:
        create = requests.post(
            f"{KEYCLOAK_URL}/admin/realms",
            headers=headers,
            json={"realm": REALM_NAME, "enabled": True, "sslRequired": "NONE"},
            timeout=30,
        )
        create.raise_for_status()
        return
    existing.raise_for_status()


def _realm_client_uuid(headers: dict[str, str], client_id: str) -> str | None:
    response = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/clients",
        headers=headers,
        params={"clientId": client_id},
        timeout=30,
    )
    response.raise_for_status()
    clients = response.json()
    return clients[0]["id"] if clients else None


def _client_secret(headers: dict[str, str], client_id: str) -> str:
    client_uuid = _realm_client_uuid(headers, client_id)
    assert client_uuid, f"Client {client_id} not found"
    response = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/clients/{client_uuid}/client-secret",
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["value"]


def _ensure_client(
    headers: dict[str, str],
    client_id: str,
    *,
    public: bool,
    redirect_uris: list[str],
    direct_access: bool = False,
    secret: str | None = None,
) -> None:
    payload = {
        "clientId": client_id,
        "name": client_id,
        "enabled": True,
        "publicClient": public,
        "redirectUris": redirect_uris,
        "directAccessGrantsEnabled": direct_access,
        "standardFlowEnabled": True,
        "secret": secret,
    }
    existing_id = _realm_client_uuid(headers, client_id)
    if existing_id is None:
        response = requests.post(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/clients",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        return

    response = requests.put(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/clients/{existing_id}",
        headers=headers,
        json=payload,
        timeout=30,
    )
    response.raise_for_status()


def _client_representation(headers: dict[str, str], client_id: str) -> dict:
    client_uuid = _realm_client_uuid(headers, client_id)
    assert client_uuid, f"Client {client_id} not found"
    response = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/clients/{client_uuid}",
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def _update_client(headers: dict[str, str], client_id: str, **updates) -> None:
    client_uuid = _realm_client_uuid(headers, client_id)
    assert client_uuid, f"Client {client_id} not found"
    payload = _client_representation(headers, client_id)
    payload.update(updates)
    response = requests.put(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/clients/{client_uuid}",
        headers=headers,
        json=payload,
        timeout=30,
    )
    response.raise_for_status()


def _ensure_client_scope_assigned(
    headers: dict[str, str],
    client_id: str,
    scope_name: str,
    *,
    optional: bool = True,
) -> None:
    client_uuid = _realm_client_uuid(headers, client_id)
    assert client_uuid, f"Client {client_id} not found"
    scopes_response = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/client-scopes",
        headers=headers,
        timeout=30,
    )
    scopes_response.raise_for_status()
    scope = next(item for item in scopes_response.json() if item["name"] == scope_name)
    route = "optional-client-scopes" if optional else "default-client-scopes"
    current_response = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/clients/{client_uuid}/{route}",
        headers=headers,
        timeout=30,
    )
    current_response.raise_for_status()
    if any(item["name"] == scope_name for item in current_response.json()):
        return
    response = requests.put(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/clients/{client_uuid}/{route}/{scope['id']}",
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()


def _ensure_client_protocol_mapper(
    headers: dict[str, str],
    client_id: str,
    mapper_name: str,
    protocol_mapper: str,
    config: dict[str, str],
) -> None:
    client_uuid = _realm_client_uuid(headers, client_id)
    assert client_uuid, f"Client {client_id} not found"
    response = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/clients/{client_uuid}/protocol-mappers/models",
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    existing = next(
        (item for item in response.json() if item["name"] == mapper_name), None
    )
    payload = {
        "name": mapper_name,
        "protocol": "openid-connect",
        "protocolMapper": protocol_mapper,
        "consentRequired": False,
        "config": config,
    }
    if existing is None:
        create = requests.post(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/clients/{client_uuid}/protocol-mappers/models",
            headers=headers,
            json=payload,
            timeout=30,
        )
        create.raise_for_status()
        return
    payload["id"] = existing["id"]
    update = requests.put(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/clients/{client_uuid}/protocol-mappers/models/{existing['id']}",
        headers=headers,
        json=payload,
        timeout=30,
    )
    update.raise_for_status()


def _user_id(headers: dict[str, str], username: str) -> str | None:
    response = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users",
        headers=headers,
        params={"username": username},
        timeout=30,
    )
    response.raise_for_status()
    users = [user for user in response.json() if user["username"] == username]
    return users[0]["id"] if users else None


def _ensure_user(
    headers: dict[str, str],
    username: str,
    password: str,
    *,
    email: str,
    first_name: str,
    last_name: str,
) -> None:
    payload = {
        "username": username,
        "enabled": True,
        "email": email,
        "emailVerified": False,
        "firstName": first_name,
        "lastName": last_name,
    }
    user_id = _user_id(headers, username)
    if user_id is None:
        response = requests.post(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        user_id = _user_id(headers, username)
        assert user_id, f"User {username} was not created"
    else:
        response = requests.put(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users/{user_id}",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()

    response = requests.put(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users/{user_id}/reset-password",
        headers=headers,
        json={"type": "password", "value": password, "temporary": False},
        timeout=30,
    )
    response.raise_for_status()


def _ensure_role(headers: dict[str, str], role_name: str) -> None:
    get_response = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/roles/{role_name}",
        headers=headers,
        timeout=30,
    )
    if get_response.status_code == 404:
        create_response = requests.post(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/roles",
            headers=headers,
            json={"name": role_name},
            timeout=30,
        )
        create_response.raise_for_status()
        return
    get_response.raise_for_status()


def _assign_role_to_user_api(
    headers: dict[str, str], username: str, role_name: str
) -> None:
    user_id = _user_id(headers, username)
    assert user_id, f"User {username} not found"
    role = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/roles/{role_name}",
        headers=headers,
        timeout=30,
    )
    role.raise_for_status()
    current = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users/{user_id}/role-mappings/realm",
        headers=headers,
        timeout=30,
    )
    current.raise_for_status()
    if any(existing["name"] == role_name for existing in current.json()):
        return
    assign = requests.post(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users/{user_id}/role-mappings/realm",
        headers=headers,
        json=[role.json()],
        timeout=30,
    )
    assign.raise_for_status()


def _enable_realm_roles_in_id_token_api(headers: dict[str, str]) -> None:
    scopes_response = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/client-scopes",
        headers=headers,
        timeout=30,
    )
    scopes_response.raise_for_status()
    roles_scope = next(
        scope for scope in scopes_response.json() if scope["name"] == "roles"
    )
    mappers_response = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/client-scopes/{roles_scope['id']}/protocol-mappers/models",
        headers=headers,
        timeout=30,
    )
    mappers_response.raise_for_status()
    mapper = next(
        item for item in mappers_response.json() if item["name"] == "realm roles"
    )
    mapper["config"]["id.token.claim"] = "true"
    update_response = requests.put(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/client-scopes/{roles_scope['id']}/protocol-mappers/models/{mapper['id']}",
        headers=headers,
        json=mapper,
        timeout=30,
    )
    update_response.raise_for_status()


def _realm_representation(headers: dict[str, str]) -> dict:
    response = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}",
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def _update_realm(headers: dict[str, str], **updates) -> None:
    payload = _realm_representation(headers)
    payload.update(updates)
    response = requests.put(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}",
        headers=headers,
        json=payload,
        timeout=30,
    )
    response.raise_for_status()


def _ensure_group(headers: dict[str, str], group_name: str) -> str:
    response = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/groups",
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    groups = response.json()
    existing = next((group for group in groups if group["name"] == group_name), None)
    if existing:
        return existing["id"]

    create = requests.post(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/groups",
        headers=headers,
        json={"name": group_name},
        timeout=30,
    )
    create.raise_for_status()
    return _ensure_group(headers, group_name)


def _assign_role_to_group_api(
    headers: dict[str, str], group_name: str, role_name: str
) -> None:
    group_id = _ensure_group(headers, group_name)
    role = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/roles/{role_name}",
        headers=headers,
        timeout=30,
    )
    role.raise_for_status()
    current = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/groups/{group_id}/role-mappings/realm",
        headers=headers,
        timeout=30,
    )
    current.raise_for_status()
    if any(existing["name"] == role_name for existing in current.json()):
        return
    response = requests.post(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/groups/{group_id}/role-mappings/realm",
        headers=headers,
        json=[role.json()],
        timeout=30,
    )
    response.raise_for_status()


def _add_user_to_group_api(
    headers: dict[str, str], username: str, group_name: str
) -> None:
    user_id = _user_id(headers, username)
    group_id = _ensure_group(headers, group_name)
    assert user_id, f"User {username} not found"
    response = requests.put(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users/{user_id}/groups/{group_id}",
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()


def _set_password_policy_api(headers: dict[str, str], policy: str) -> None:
    _update_realm(headers, passwordPolicy=policy)


def _configure_smtp_api(
    headers: dict[str, str], host: str, port: str, from_addr: str
) -> None:
    _update_realm(
        headers,
        smtpServer={
            "host": host,
            "port": str(port),
            "from": from_addr,
            "fromDisplayName": from_addr,
        },
    )


def _add_required_action_api(
    headers: dict[str, str], username: str, action: str
) -> None:
    user_id = _user_id(headers, username)
    assert user_id, f"User {username} not found"
    response = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users/{user_id}",
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    current_actions = set(payload.get("requiredActions", []))
    current_actions.add(action)
    payload["requiredActions"] = sorted(current_actions)
    update = requests.put(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users/{user_id}",
        headers=headers,
        json=payload,
        timeout=30,
    )
    update.raise_for_status()


def _set_user_attribute_api(
    headers: dict[str, str], username: str, key: str, value: str
) -> None:
    user_id = _user_id(headers, username)
    assert user_id, f"User {username} not found"
    response = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users/{user_id}",
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    attributes = payload.get("attributes", {})
    attributes[key] = [value]
    payload["attributes"] = attributes
    update = requests.put(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users/{user_id}",
        headers=headers,
        json=payload,
        timeout=30,
    )
    update.raise_for_status()


def _trigger_actions_email_api(
    headers: dict[str, str], username: str, actions: list[str]
) -> None:
    user_id = _user_id(headers, username)
    assert user_id, f"User {username} not found"
    response = requests.put(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users/{user_id}/execute-actions-email",
        headers=headers,
        json=actions,
        timeout=30,
    )
    response.raise_for_status()


def _ensure_user_profile_attribute(
    headers: dict[str, str],
    name: str,
    *,
    display_name: str | None = None,
) -> None:
    response = requests.get(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users/profile",
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    attributes = payload.get("attributes", [])
    if any(attribute["name"] == name for attribute in attributes):
        return
    attributes.append(
        {
            "name": name,
            "displayName": display_name or name,
            "permissions": {"view": ["admin", "user"], "edit": ["admin", "user"]},
            "multivalued": False,
        }
    )
    update = requests.put(
        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users/profile",
        headers=headers,
        json=payload,
        timeout=30,
    )
    update.raise_for_status()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    outcome = yield
    setattr(item, f"rep_{call.when}", outcome.get_result())


@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def tests_root() -> Path:
    return TESTS_ROOT


@pytest.fixture(scope="session")
def artifacts_root() -> Path:
    return ARTIFACTS_ROOT


@pytest.fixture(scope="session")
def workspace_manager(pytestconfig: pytest.Config) -> WorkspaceManager:
    manager = WorkspaceManager(
        source_root=PROJECT_ROOT,
        tests_root=TESTS_ROOT,
        keep_workspaces=pytestconfig.getoption("--keep-workspaces"),
    )
    yield manager
    manager.cleanup()


@pytest.fixture
def workspace_factory(workspace_manager: WorkspaceManager):
    created: list[Path] = []

    def _factory(name: str, *solutions: str) -> Path:
        workspace = workspace_manager.create(name)
        for solution in solutions:
            workspace_manager.apply_solution(workspace, solution)
        created.append(workspace)
        return workspace

    return _factory


@pytest.fixture(scope="session")
def docker_stack() -> DockerStack:
    return DockerStack(PROJECT_ROOT)


@pytest.fixture(scope="session")
def infra(docker_stack: DockerStack):
    docker_stack.down(volumes=True)
    for port in (8080, 1080, 1025, 389, 6443):
        _assert_port_available(port)

    docker_stack.up("postgres", "keycloak", "openldap", "phpldapadmin", "smtp")

    wait_for_http(
        f"{KEYCLOAK_URL}/realms/master/.well-known/openid-configuration", max_wait=180
    )
    wait_for_http(MAILDEV_URL, max_wait=60)

    yield docker_stack

    docker_stack.down(volumes=True)


@pytest.fixture(scope="session")
def seed_training_realm(infra, playwright):
    _ensure_training_realm()
    headers = _admin_headers()
    _ensure_client(
        headers,
        SECRET_WEBAPP_CLIENT,
        public=False,
        redirect_uris=["http://localhost:8090/*"],
    )
    _ensure_client(
        headers,
        CURL_CLIENT,
        public=True,
        redirect_uris=["http://localhost:*"],
        direct_access=True,
    )
    _ensure_client(
        headers, VUE_CLIENT, public=True, redirect_uris=["http://localhost:8070/*"]
    )
    _ensure_user(
        headers,
        TEST_USER,
        TEST_PASSWORD,
        email=f"{TEST_USER}@example.com",
        first_name="Test",
        last_name="User",
    )
    _ensure_role(headers, "ROLE_ADMIN")
    _ensure_role(headers, "ROLE_USER")
    _assign_role_to_user_api(headers, TEST_USER, "ROLE_ADMIN")
    _assign_role_to_user_api(headers, TEST_USER, "ROLE_USER")
    _enable_realm_roles_in_id_token_api(headers)

    browser = playwright.chromium.launch(
        headless=True, args=["--ignore-certificate-errors"]
    )
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    page.set_default_timeout(20_000)

    login_to_realm_console(
        page, KEYCLOAK_URL, REALM_NAME, KEYCLOAK_ADMIN_USER, KEYCLOAK_ADMIN_PASS
    )

    context.close()
    browser.close()


@pytest.fixture
def process_manager(tmp_path: Path) -> ProcessManager:
    manager = ProcessManager(tmp_path / "process-logs")
    yield manager
    manager.stop_all()


@pytest.fixture
def admin_page(seed_training_realm, browser):
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    page.set_default_timeout(20_000)
    login_to_realm_console(
        page, KEYCLOAK_URL, REALM_NAME, KEYCLOAK_ADMIN_USER, KEYCLOAK_ADMIN_PASS
    )
    yield page
    context.close()


@pytest.fixture
def capture_page_artifacts(request: pytest.FixtureRequest, artifacts_root: Path):
    pages = []

    def _register(page, name: str = "page") -> None:
        pages.append((page, name))

    yield _register

    failed = (
        getattr(request.node, "rep_setup", None) and request.node.rep_setup.failed
    ) or (getattr(request.node, "rep_call", None) and request.node.rep_call.failed)
    if not failed:
        return

    target_dir = artifacts_root / request.node.name
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    for index, (page, name) in enumerate(pages, start=1):
        try:
            page.screenshot(path=target_dir / f"{index:02d}-{name}.png", full_page=True)
            (target_dir / f"{index:02d}-{name}.html").write_text(
                page.content(), encoding="utf-8"
            )
        except Exception:
            continue


@pytest.fixture(scope="session")
def keycloak_issuer() -> str:
    return f"{KEYCLOAK_URL}/realms/{REALM_NAME}"


@pytest.fixture(scope="session")
def base_env() -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("CI", "1")
    return env

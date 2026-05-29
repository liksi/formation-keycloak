from __future__ import annotations

import subprocess
import time

import pytest
import requests


def _wait_for_kc_ready(mgmt_port: int, max_wait: int = 120) -> None:
    """Poll /health/ready until Keycloak is fully initialized.

    KC 26.x returns HTTP 200 with {"status": "DOWN"} while still starting,
    so checking HTTP status alone is not sufficient."""
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            r = requests.get(f"http://localhost:{mgmt_port}/health/ready", timeout=5)
            if r.status_code == 200 and r.json().get("status") == "UP":
                return
        except (requests.RequestException, ValueError):
            pass
        time.sleep(2)
    raise TimeoutError(f"Keycloak not ready on management port {mgmt_port} after {max_wait}s")

KC_IMAGE = "quay.io/keycloak/keycloak:26.6.2"
KC_DEV_HTTP_PORT = 8082
KC_DEV_MGMT_PORT = 9002
KC_PROD_HTTP_PORT = 8083
KC_PROD_MGMT_PORT = 9003


@pytest.fixture(scope="module")
def keycloak_dev_container():
    container = "kc-pw4-dev"
    subprocess.run(
        [
            "docker", "run", "-d",
            "--name", container,
            "-e", "KC_BOOTSTRAP_ADMIN_USERNAME=admin",
            "-e", "KC_BOOTSTRAP_ADMIN_PASSWORD=secret",
            "-e", "KC_HEALTH_ENABLED=true",
            "-e", "KC_METRICS_ENABLED=true",
            "-p", f"{KC_DEV_HTTP_PORT}:8080",
            "-p", f"{KC_DEV_MGMT_PORT}:9000",
            KC_IMAGE,
            "start-dev",
        ],
        check=True,
    )
    try:
        _wait_for_kc_ready(KC_DEV_MGMT_PORT, max_wait=120)
        yield f"http://localhost:{KC_DEV_HTTP_PORT}"
    finally:
        subprocess.run(["docker", "stop", container], check=False)
        subprocess.run(["docker", "rm", container], check=False)


@pytest.fixture(scope="module")
def keycloak_prod_container(infra):
    """Starts KC in production mode on separate ports, reusing infra postgres.
    Uses bridge networking + port mappings so the container's internal port 9000
    (management, baked at build time) maps to a free host port without conflicting
    with the infra KC that also uses host port 9000."""
    container = "kc-pw4-prod"
    subprocess.run(
        [
            "docker", "run", "-d",
            "--name", container,
            # Bridge networking: internal 8080/9000 map to 8083/9003 on the host.
            # host.docker.internal resolves to the docker bridge gateway so the
            # container can reach the host-mapped postgres port.
            "--add-host=host.docker.internal:host-gateway",
            "-p", f"{KC_PROD_HTTP_PORT}:8080",
            "-p", f"{KC_PROD_MGMT_PORT}:9000",
            "-e", "KC_BOOTSTRAP_ADMIN_USERNAME=admin",
            "-e", "KC_BOOTSTRAP_ADMIN_PASSWORD=secret",
            "-e", "KC_HTTP_ENABLED=true",
            "-e", "KC_HOSTNAME_STRICT=false",
            "-e", "KC_DB_URL_HOST=host.docker.internal",
            "-e", "KC_DB_URL_PORT=5432",
            "-e", "KC_DB_URL_DATABASE=keycloak",
            "-e", "KC_DB_USERNAME=user",
            "-e", "KC_DB_PASSWORD=pwd",
            # JDBC_PING: use shared postgres for cluster member discovery
            "-e", "KC_CACHE_STACK=jdbc-ping",
            "keycloak:latest",
        ],
        check=True,
    )
    try:
        _wait_for_kc_ready(KC_PROD_MGMT_PORT, max_wait=120)
        yield f"http://localhost:{KC_PROD_HTTP_PORT}"
    finally:
        subprocess.run(["docker", "stop", container], check=False)
        subprocess.run(["docker", "rm", container], check=False)


@pytest.mark.pw4
def test_dev_mode_admin_console_accessible(keycloak_dev_container):
    base = keycloak_dev_container
    response = requests.get(f"{base}/admin/", timeout=10, allow_redirects=True)
    assert response.status_code == 200


@pytest.mark.pw4
def test_health_live(keycloak_dev_container):
    response = requests.get(
        f"http://localhost:{KC_DEV_MGMT_PORT}/health/live", timeout=10
    )
    assert response.status_code == 200
    assert response.json()["status"] == "UP"


@pytest.mark.pw4
def test_health_ready(keycloak_dev_container):
    response = requests.get(
        f"http://localhost:{KC_DEV_MGMT_PORT}/health/ready", timeout=10
    )
    assert response.status_code == 200
    assert response.json()["status"] == "UP"


@pytest.mark.pw4
def test_metrics_endpoint(keycloak_dev_container):
    response = requests.get(
        f"http://localhost:{KC_DEV_MGMT_PORT}/metrics", timeout=10
    )
    assert response.status_code == 200
    assert "jvm_memory_used_bytes" in response.text


@pytest.mark.pw4
@pytest.mark.slow
@pytest.mark.timeout(300)
def test_prod_mode_admin_console_accessible(keycloak_prod_container):
    base = keycloak_prod_container
    response = requests.get(f"{base}/admin/", timeout=10, allow_redirects=True)
    assert response.status_code == 200


@pytest.mark.pw4
@pytest.mark.slow
@pytest.mark.timeout(300)
def test_prod_mode_health_ready(keycloak_prod_container):
    response = requests.get(
        f"http://localhost:{KC_PROD_MGMT_PORT}/health/ready", timeout=10
    )
    assert response.status_code == 200
    assert response.json()["status"] == "UP"


@pytest.mark.pw4
@pytest.mark.slow
@pytest.mark.timeout(300)
def test_prod_mode_cluster_formation(keycloak_prod_container):
    result = subprocess.run(
        ["docker", "logs", "kc-pw4-prod"],
        capture_output=True,
        text=True,
        check=False,
    )
    logs = result.stdout + result.stderr
    cluster_signals = ["ISPN000094", "Joined cluster", "joined the cluster", "cluster view"]
    assert any(signal.lower() in logs.lower() for signal in cluster_signals), (
        f"No cluster join signal found in logs. Last 500 chars: {logs[-500:]}"
    )

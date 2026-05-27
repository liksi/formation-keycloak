from __future__ import annotations

import os
import signal
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import requests


@dataclass
class ManagedProcess:
    name: str
    process: subprocess.Popen
    log_path: Path


class DockerStack:
    CONTAINER_NAMES = (
        "postgres",
        "keycloak",
        "openldap",
        "ldap-admin",
        "smtp",
        "api",
        "secret-webapp",
        "vue-app",
        "oauth2-proxy",
    )

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root

    def up(self, *services: str) -> None:
        self.remove_named_containers()
        cmd = ["docker", "compose", "up", "-d", *services]
        subprocess.run(cmd, cwd=self.project_root, check=True)

    def up_no_deps(self, *services: str) -> None:
        cmd = ["docker", "compose", "up", "-d", "--no-deps", *services]
        subprocess.run(cmd, cwd=self.project_root, check=True)

    def down(self, volumes: bool = False) -> None:
        cmd = ["docker", "compose", "down"]
        if volumes:
            cmd.append("-v")
        subprocess.run(cmd, cwd=self.project_root, check=False, capture_output=True)
        self.remove_named_containers()

    def rm(self, *services: str) -> None:
        if not services:
            return
        subprocess.run(
            ["docker", "compose", "rm", "-sf", *services],
            cwd=self.project_root,
            check=False,
            capture_output=True,
        )

    def logs(self, service: str, tail: int = 200) -> str:
        result = subprocess.run(
            ["docker", "compose", "logs", f"--tail={tail}", service],
            cwd=self.project_root,
            check=False,
            capture_output=True,
            text=True,
        )
        return result.stdout + result.stderr

    def remove_named_containers(self) -> None:
        subprocess.run(
            ["docker", "rm", "-f", *self.CONTAINER_NAMES],
            cwd=self.project_root,
            check=False,
            capture_output=True,
        )


class ProcessManager:
    def __init__(self, logs_dir: Path) -> None:
        self.logs_dir = logs_dir
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._processes: list[ManagedProcess] = []

    def start(
        self,
        name: str,
        cmd: list[str],
        cwd: Path,
        port: int | None = None,
        ready_check=None,
        env: dict[str, str] | None = None,
        timeout: int = 180,
    ) -> ManagedProcess:
        if port is not None:
            self.assert_port_available(port, name)
        log_path = self.logs_dir / f"{name}.log"
        with log_path.open("w", encoding="utf-8") as log_file:
            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                env=env or os.environ.copy(),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
                start_new_session=True,
            )
        managed = ManagedProcess(name=name, process=process, log_path=log_path)
        self._processes.append(managed)
        if ready_check is not None:
            self._wait_until_ready(managed, ready_check, timeout)
        return managed

    def stop_all(self) -> None:
        for managed in reversed(self._processes):
            process = managed.process
            if process.poll() is not None:
                continue
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
        self._processes.clear()

    def read_log(self, name: str) -> str:
        for managed in self._processes:
            if managed.name == name and managed.log_path.exists():
                return managed.log_path.read_text(encoding="utf-8")
        return ""

    def start_secret_webapp(
        self, workspace: Path, env: dict[str, str] | None = None
    ) -> ManagedProcess:
        return self.start(
            "secret-webapp",
            ["./mvnw", "spring-boot:run"],
            cwd=workspace / "secret-webapp",
            port=8090,
            ready_check=self._secret_webapp_ready,
            env=env,
        )

    def start_api(
        self, workspace: Path, env: dict[str, str] | None = None
    ) -> ManagedProcess:
        return self.start(
            "api",
            ["./mvnw", "spring-boot:run"],
            cwd=workspace / "api",
            port=8091,
            ready_check=self._api_ready,
            env=env,
        )

    def install_vue_dependencies(
        self, workspace: Path, env: dict[str, str] | None = None
    ) -> None:
        subprocess.run(
            ["npm", "install"],
            cwd=workspace / "vue-app",
            env=env or os.environ.copy(),
            check=True,
        )

    def start_vue_app(
        self, workspace: Path, env: dict[str, str] | None = None
    ) -> ManagedProcess:
        return self.start(
            "vue-app",
            ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "8070"],
            cwd=workspace / "vue-app",
            port=8070,
            ready_check=self._vue_app_ready,
            env=env,
            timeout=240,
        )

    def assert_port_available(self, port: int, name: str) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                raise RuntimeError(
                    f"Port {port} is already in use before starting {name}. "
                    "Stop the existing process or rerun after cleaning stale lab services."
                )

    def _wait_until_ready(
        self, managed: ManagedProcess, ready_check, timeout: int
    ) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if managed.process.poll() is not None:
                raise RuntimeError(
                    f"{managed.name} exited before becoming ready.\n\n{managed.log_path.read_text(encoding='utf-8')}"
                )
            try:
                if ready_check():
                    return
            except requests.RequestException:
                pass
            time.sleep(1)
        raise TimeoutError(
            f"Timed out waiting for {managed.name} to become ready.\n\n{managed.log_path.read_text(encoding='utf-8')}"
        )

    @staticmethod
    def _secret_webapp_ready() -> bool:
        response = requests.get("http://127.0.0.1:8090/", timeout=5)
        return (
            response.status_code == 200
            and "Welcome to the secret web app" in response.text
        )

    @staticmethod
    def _api_ready() -> bool:
        response = requests.get("http://127.0.0.1:8091/messages/public", timeout=5)
        return (
            response.status_code == 200
            and response.json()["message"] == "Hello, this is not protected"
        )

    @staticmethod
    def _vue_app_ready() -> bool:
        response = requests.get("http://127.0.0.1:8070/", timeout=5)
        return response.status_code == 200 and "vite" in response.text.lower()

    @staticmethod
    def _oauth2_proxy_ready() -> bool:
        response = requests.get(
            "http://127.0.0.1:4180/", timeout=5, allow_redirects=False
        )
        return response.status_code in (
            302,
            303,
        ) and "oauth2/start" in response.headers.get("Location", "")

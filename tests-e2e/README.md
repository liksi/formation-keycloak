# End-to-End Test Suite

This suite validates the practical work exercises against a locally running lab stack.
It acts as the reference solution checker: each test verifies that the expected behaviour
holds once the student has completed the corresponding exercise.

## Setup

Prerequisites: Python 3.10+, `uv`, Docker Compose v2, Node.js 22+, Maven 3.9+.

```bash
cd tests-e2e
uv sync
uv run playwright install chromium
```

## Running tests

```bash
# Full suite (slow — starts/stops Docker, compiles apps)
uv run pytest

# Skip long-running tests (app compilation, Docker restarts)
uv run pytest -m "not slow"

# One practical work at a time
uv run pytest -m pw1
uv run pytest -m pw2
uv run pytest -m pw3
uv run pytest -m pw5
uv run pytest -m pw6
uv run pytest -m pw7

# One file
uv run pytest test_pw1_auth_modes.py -q

# Keep /tmp workspaces after the run (useful for debugging)
uv run pytest --keep-workspaces
```

Test markers are defined in `pyproject.toml`. A 120-second per-test timeout is set by default.

---

## Architecture

```
tests-e2e/
├── conftest.py          # Fixtures, Keycloak Admin API helpers, realm seeding
├── pyproject.toml       # Dependencies and pytest configuration
├── helpers/
│   ├── http_.py         # wait_for_http
│   ├── keycloak_ui.py   # Playwright helpers for Keycloak Admin Console (Keycloak 26 / PatternFly v5)
│   ├── oidc.py          # Token generation, JWT decode, userinfo
│   ├── maildev.py       # Poll MailDev API until a message arrives
│   ├── ldap.py          # ldap3-based LDAP operations (create users/groups, sync)
│   ├── stack.py         # DockerStack (docker compose wrapper) and ProcessManager
│   └── workspace.py     # Disposable /tmp workspace creation and solution patching
├── solutions/           # Reference .patch files (documentation only — not used at runtime)
├── artifacts/           # Screenshots and HTML snapshots saved on test failure
└── test_pw*.py          # Test files, one per practical work
```

---

## Core design decisions

### 1. Disposable `/tmp` workspaces

The practical work exercises are represented by `FIXME` markers in the source code.
Tests that require student changes cannot modify the working tree (it would corrupt
the training material). Instead, every test that needs code changes:

1. Copies the entire project into a fresh `/tmp/formation-keycloak-<name>-XXXXX/repo/` directory
   via `WorkspaceManager.create()`.
2. Applies one or more named solutions via `WorkspaceManager.apply_solution()`.
3. Starts the app(s) from that disposable copy.
4. After the test, the workspace is deleted (unless `--keep-workspaces` is passed).

This guarantees the source tree is never touched, tests are fully independent,
and the student's in-progress work is never at risk.

The `shutil.copytree` excludes build artifacts (`.git`, `target/`, `node_modules/`,
`.venv/`, etc.) so copies are fast and Maven/npm do a clean build in the workspace.

### 2. Solution application: text search-and-replace, not patches

`WorkspaceManager.apply_solution()` uses hardcoded string replacements (`_replace_checked`)
instead of the `.patch` files in `solutions/`. The `.patch` files are documentation
references only — they are not applied at runtime.

The reason for text replacement over patches is **robustness**: patches fail on any
surrounding whitespace or context change. Text replacement only requires the exact
`FIXME`-adjacent snippet to be stable, which is a much weaker requirement and survives
most reformatting.

`_replace_checked` is idempotent: it skips the replacement if the `new` string is already
present, so applying the same solution twice doesn't raise. This avoids issues when
solutions are composed (e.g., `pw7_required_action` also calls `_apply_pw7_theme_enable`).

### 3. Fixture chain and session-scoped setup

The fixture dependency chain is:

```
infra (session)
 └── seed_training_realm (session)
      └── admin_page (function)
```

- **`infra`**: Tears down any running stack, checks that required ports are free, starts
  only the infrastructure services (Postgres, Keycloak, OpenLDAP, phpLDAPadmin, MailDev),
  and waits for Keycloak's OIDC discovery endpoint to be healthy. Volumes are wiped on both
  setup and teardown to guarantee a clean state between full runs.

- **`seed_training_realm`**: Creates the `training` realm and seeds it with all
  necessary objects via the Keycloak Admin REST API (not the UI): realm, clients
  (`secret-webapp`, `curl`, `vue`), test user (`test` / `pwd`), roles
  (`ROLE_ADMIN`, `ROLE_USER`), and role assignments. Also enables realm roles in the
  ID token. Runs once per session — subsequent tests reuse the seeded realm.

  A Playwright browser is opened at the end of `seed_training_realm` to log into the
  Admin Console. This pre-warms the browser session for fixtures that need it
  (`admin_page`), and also triggers the Keycloak realm console cache so the first
  test doesn't hit a cold-start delay.

- **`admin_page`**: Function-scoped. Opens a fresh browser context, navigates to the
  Admin Console already logged in to the `training` realm. Each test gets an isolated
  browser context (no cookie leakage between tests).

### 4. Two API interaction styles

Most setup is done via the **Keycloak Admin REST API** (in `conftest.py`). This is faster,
more reliable, and does not depend on the Keycloak UI layout. Functions follow the
`_ensure_*` naming convention — they are idempotent: they create the resource if absent,
update it if it already exists, and skip silently if nothing needs to change.

**Playwright UI automation** is used only when:
- A test is specifically validating a UI interaction (e.g., `admin_page` fixtures).
- An operation is only exposed via the UI (e.g., LDAP federation sync in PW6).

This separation avoids brittle UI-only test setups for things that can be done via API.

### 5. ProcessManager: process groups and readiness polling

`ProcessManager.start()` launches Spring Boot (`./mvnw spring-boot:run`) and Vite
(`npm run dev`) as subprocess groups (`start_new_session=True`). On teardown, it sends
`SIGTERM` to the entire process group via `os.killpg`, not just the parent PID. Without
this, the JVM spawned by Maven would outlive the test and keep the port bound, causing
port-collision errors on the next test.

All processes are polled for readiness via HTTP before the test body runs:
- `secret-webapp`: expects `200` with `"Welcome to the secret web app"` on `/`
- `api`: expects `200` with `{"message": "Hello, this is not protected"}` on `/messages/public`
- `vue-app`: expects `200` with `"vite"` in the HTML on `/`

If the process exits before becoming ready, the full log is included in the exception
message to make failures easy to diagnose.

### 6. Port collision detection

The `infra` fixture and `ProcessManager.assert_port_available()` both check that the
required ports are free before starting anything. This gives a clear, human-readable
error (`"Port 8090 is already in use before starting secret-webapp"`) instead of a
cryptic Docker or Maven failure that would be hard to trace back to a stale process.

### 7. PatternFly v5 backdrop handling

Keycloak 26 uses PatternFly v5, which animates modal backdrops. A backdrop can linger
for hundreds of milliseconds after a modal is dismissed, blocking clicks on elements
underneath. The `_dismiss_backdrop` helper in `keycloak_ui.py` uses a three-step
strategy:

1. Wait up to 5s for `.pf-v5-c-backdrop` to detach naturally.
2. If still present, press `Escape`.
3. If that fails, continue anyway.

This pattern appears wherever a modal interaction (e.g., password confirmation dialog)
could leave a backdrop. Without it, the next `page.click()` would randomly fail with
"element intercepted" depending on animation timing.

### 8. DockerStack for PW6 (oauth2-proxy)

PW6 tests `oauth2-proxy`, which runs as a Docker container (not a local process). The
test creates a workspace, patches the `docker-compose.yml` with the generated client
secret and correct realm URL, and then uses a second `DockerStack` instance pointing at
that workspace to start only the `oauth2-proxy` container (`--no-deps`). The app-under-test
(`secret-webapp`) runs as a local process via `ProcessManager` to allow workspace patching.

The `DockerStack.rm("oauth2-proxy")` in the `finally` block ensures the container is
always stopped, even if the test fails, so it doesn't interfere with subsequent runs.

### 9. Artifact capture on failure

`capture_page_artifacts` is a function-scoped fixture that test functions can call to
register Playwright `Page` objects. If the test fails, it saves a full-page screenshot
(`.png`) and the page HTML (`.html`) for each registered page into
`tests-e2e/artifacts/<test-name>/`. These files are committed to help diagnose CI failures
without having to re-run the full suite.

---

## Test file map

| File | Marker | What it validates |
|------|--------|-------------------|
| `test_pw1_auth_modes.py` | `pw1` | `none`, `basic`, and `form` authentication modes on `secret-webapp` |
| `test_pw2_oidc_local.py` | `pw2` | OIDC discovery, direct grant, token refresh, userinfo endpoint, `openid` scope requirement |
| `test_pw3_keycloak_config.py` | `pw3` | `secret-webapp` delegating auth to local Keycloak; groups/roles/email flows via Admin API |
| `test_pw5_api_spa.py` | `pw5` | JWT-protected `api` resource server; Vue SPA startup with bearer token injection |
| `test_pw6_enterprise.py` | `pw6` | Events config, LDAP federation and sync, `oauth2-proxy` full auth flow via Docker |
| `test_pw7_customization.py` | `pw7` | Workspace patching for theme, AgeMapper, UpdateQuestionAction, QuestionAuthenticator |

Tests marked `slow` involve Docker restarts or `npm install` + app compilation and can
take several minutes each. The rest run in seconds once the `infra` fixture is up.

---

## Practical notes

**Re-running after a failure**: the `infra` fixture wipes volumes on setup, so state from
a previous run is always cleaned. You don't need to `docker compose down -v` manually
before re-running.

**Debugging a workspace**: run with `--keep-workspaces` and look in `/tmp/formation-keycloak-*/`.
Process logs are written to `<tmp_path>/process-logs/<name>.log`.

**Running a single test with verbose output**:
```bash
uv run pytest test_pw3_keycloak_config.py::test_pw3_secret_webapp_can_delegate_to_local_keycloak -s -v
```

**Port conflicts**: if tests fail with "Port X is already in use", a previous test run
left a stale process. Find it with `lsof -i :8090` (or 8091 / 8070 / 4180) and kill it.

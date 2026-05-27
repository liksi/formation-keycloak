from __future__ import annotations

from playwright.sync_api import Page


def _console_url(base_url: str) -> str:
    return f"{base_url}/admin/master/console/"


def _goto(page: Page, base_url: str, realm_name: str, fragment: str) -> None:
    page.goto(
        f"{_console_url(base_url)}#{realm_name}/{fragment}",
        wait_until="domcontentloaded",
    )
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(600)
    _dismiss_alerts(page)
    _dismiss_backdrop(page)


def _dismiss_backdrop(page: Page) -> None:
    try:
        page.locator(".pf-v5-c-backdrop").wait_for(state="detached", timeout=5000)
    except Exception:
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(250)
        except Exception:
            pass


def _dismiss_alerts(page: Page) -> None:
    try:
        for button in page.get_by_role("button", name="Close alert").all():
            try:
                button.click()
            except Exception:
                continue
    except Exception:
        pass


def _save(page: Page) -> None:
    save_button = page.get_by_role("button", name="Save")
    if save_button.count():
        save_button.last.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(600)
    _dismiss_alerts(page)


def login_to_master_console(
    page: Page,
    base_url: str,
    username: str = "admin",
    password: str = "admin",
) -> None:
    page.goto(_console_url(base_url), wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    if page.get_by_role("textbox", name="Username or email").count():
        page.get_by_role("textbox", name="Username or email").fill(username)
        page.get_by_role("textbox", name="Password").fill(password)
        page.get_by_role("button", name="Sign In").click()
        page.wait_for_load_state("networkidle")
    page.goto(f"{_console_url(base_url)}#/master", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")


def login_to_realm_console(
    page: Page,
    base_url: str,
    realm_name: str,
    username: str = "admin",
    password: str = "admin",
) -> None:
    login_to_master_console(page, base_url, username, password)
    _goto(page, base_url, realm_name, "")


def add_ldap_federation(
    page: Page,
    config: dict[str, str],
    base_url: str = "http://localhost:8080",
    realm_name: str = "training",
) -> None:
    _goto(page, base_url, realm_name, "user-federation")
    page.get_by_text("LDAP").first.click()
    page.wait_for_timeout(800)
    if page.get_by_label("Vendor").count():
        page.get_by_label("Vendor").select_option(config.get("vendor", "other"))
    label_map = {
        "connectionUrl": "Connection URL",
        "usersDn": "Users DN",
        "bindDn": "Bind DN",
        "bindCredential": "Bind credentials",
    }
    for key, label in label_map.items():
        if key in config and page.get_by_label(label).count():
            page.get_by_label(label).fill(config[key])
    if "editMode" in config and page.get_by_label("Edit mode").count():
        page.get_by_label("Edit mode").select_option(config["editMode"])
    _save(page)


def test_ldap_connection(page: Page) -> None:
    if page.get_by_role("button", name="Test connection").count():
        page.get_by_role("button", name="Test connection").click()
        page.wait_for_timeout(1200)
    if page.get_by_role("button", name="Test authentication").count():
        page.get_by_role("button", name="Test authentication").click()
        page.wait_for_timeout(1200)


def sync_ldap_users(page: Page) -> None:
    if page.get_by_role("button", name="Action").count():
        page.get_by_role("button", name="Action").click()
        page.wait_for_timeout(300)
    if page.get_by_text("Sync all users").count():
        page.get_by_text("Sync all users").click()
        page.wait_for_timeout(3000)

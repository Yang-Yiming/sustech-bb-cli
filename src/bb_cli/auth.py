from __future__ import annotations

import json as _json
import os
import stat
from pathlib import Path

import click
from playwright.sync_api import sync_playwright

from bb_cli.config import CAS_LOGIN_URL, CONFIG_DIR, COOKIE_FILE, BB_API_BASE


def load_cookies() -> list[dict] | None:
    """Load cookies from disk, or return None if absent/corrupt."""
    if not COOKIE_FILE.exists():
        return None
    try:
        return _json.loads(COOKIE_FILE.read_text())
    except (_json.JSONDecodeError, OSError):
        return None


def save_cookies(cookies: list[dict]) -> None:
    """Persist cookies to disk with restricted permissions."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    COOKIE_FILE.write_text(_json.dumps(cookies, indent=2))
    COOKIE_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600


def get_credentials() -> tuple[str, str]:
    """Get SID and password from env vars or interactive prompt."""
    sid = os.environ.get("BB_SID") or click.prompt("SID (student ID)")
    password = os.environ.get("BB_PASSWORD") or click.prompt("Password", hide_input=True)
    return sid, password


def cas_login(sid: str, password: str) -> list[dict]:
    """Perform CAS SSO login via headless Playwright and return cookies."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Navigate to BB SSO entry — redirects to CAS
        page.goto(CAS_LOGIN_URL, wait_until="networkidle")

        # Fill the CAS login form
        page.fill('input[name="username"]', sid)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"], input[type="submit"], .login-btn, button:has-text("登录")')

        # Wait for redirect back to Blackboard
        try:
            page.wait_for_url(f"**/{_bb_host()}/**", timeout=15000)
        except Exception:
            # Check for error messages on the CAS page
            error = page.query_selector(".login-error, .error, #msg")
            if error:
                raise click.ClickException(f"Login failed: {error.inner_text().strip()}")
            raise click.ClickException(
                "Login failed: timed out waiting for Blackboard redirect. "
                "Check your SID and password."
            )

        cookies = context.cookies()
        browser.close()
        return cookies


def _bb_host() -> str:
    from bb_cli.config import BB_DOMAIN
    return BB_DOMAIN


def validate_session(cookies: list[dict]) -> bool:
    """Check whether the stored cookies are still valid."""
    import httpx

    jar = httpx.Cookies()
    for c in cookies:
        jar.set(c["name"], c["value"], domain=c.get("domain", ""))

    try:
        r = httpx.get(f"{BB_API_BASE}/users/me", cookies=jar, timeout=10, follow_redirects=True)
        return r.status_code == 200
    except httpx.HTTPError:
        return False


def ensure_authenticated() -> list[dict]:
    """Return valid cookies, performing login if necessary."""
    cookies = load_cookies()
    if cookies and validate_session(cookies):
        return cookies

    click.echo("Session expired or missing — logging in via CAS…")
    sid, password = get_credentials()
    cookies = cas_login(sid, password)
    save_cookies(cookies)
    return cookies

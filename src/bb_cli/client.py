from __future__ import annotations

from pathlib import Path

import click
import httpx

from bb_cli.config import BB_API_BASE


class BBClient:
    """Thin wrapper around httpx for Blackboard REST API calls."""

    def __init__(self, cookies: list[dict]):
        jar = httpx.Cookies()
        for c in cookies:
            jar.set(c["name"], c["value"], domain=c.get("domain", ""))
        self._client = httpx.Client(
            base_url=BB_API_BASE,
            cookies=jar,
            timeout=30,
            follow_redirects=True,
        )
        self._raw_cookies = cookies

    # -- core helpers ----------------------------------------------------------

    def get(self, path: str, **params) -> dict:
        """GET and return parsed JSON. Raises on HTTP errors."""
        r = self._client.get(path, params=params or None)
        if r.status_code == 401:
            self._reauthenticate()
            r = self._client.get(path, params=params or None)
        if r.status_code == 404:
            raise click.ClickException(f"Not found: {path}")
        r.raise_for_status()
        return r.json()

    def get_paginated(self, path: str, **params) -> list[dict]:
        """GET with automatic pagination; returns all results."""
        results: list[dict] = []
        while True:
            data = self.get(path, **params)
            results.extend(data.get("results", []))
            paging = data.get("paging", {})
            next_page = paging.get("nextPage")
            if not next_page:
                break
            # nextPage is a relative URL like /learn/api/public/v1/...?offset=100
            # Strip the base so we can pass it to self.get()
            path = next_page.removeprefix("/learn/api/public/v1")
            params = {}  # params already embedded in nextPage URL
        return results

    def download_file(self, url: str, dest: Path) -> Path:
        """Stream-download a file to dest."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        with self._client.stream("GET", url) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_bytes(chunk_size=8192):
                    f.write(chunk)
        return dest

    # -- internal --------------------------------------------------------------

    def _reauthenticate(self):
        """Re-authenticate once on 401."""
        from bb_cli.auth import ensure_authenticated
        cookies = ensure_authenticated()
        jar = httpx.Cookies()
        for c in cookies:
            jar.set(c["name"], c["value"], domain=c.get("domain", ""))
        self._client.cookies = jar
        self._raw_cookies = cookies

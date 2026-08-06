"""HTTP client shared by Nutrition Tracker CLI commands."""

import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click
import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_CONFIG_PATH = Path("~/.config/nutritiontracker/config.json")


@dataclass(frozen=True)
class LocalConfig:
    base_url: str | None = None
    token: str | None = None


def load_local_config(path: Path) -> LocalConfig:
    expanded_path = path.expanduser()
    if not expanded_path.exists():
        return LocalConfig()
    if not expanded_path.is_file():
        raise click.ClickException(f"Config path is not a file: {expanded_path}")

    try:
        payload = json.loads(expanded_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise click.ClickException(
            f"Could not read Nutrition Tracker config {expanded_path}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise click.ClickException(
            f"Nutrition Tracker config must contain a JSON object: {expanded_path}"
        )

    values: dict[str, str | None] = {}
    for key in ("base_url", "token"):
        value = payload.get(key)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise click.ClickException(
                f"Nutrition Tracker config field {key!r} must be a non-empty string"
            )
        values[key] = value.strip() if isinstance(value, str) else None

    if values["token"] and os.name == "posix":
        mode = stat.S_IMODE(expanded_path.stat().st_mode)
        if mode & 0o077:
            raise click.ClickException(
                f"Config {expanded_path} contains a token but has mode {mode:04o}; "
                f"run: chmod 600 {expanded_path}"
            )

    return LocalConfig(base_url=values["base_url"], token=values["token"])


class APIClient:
    def __init__(self, base_url: str, token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | list[tuple[str, str]] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            response = httpx.request(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                params=params,
                json=json,
                timeout=10,
            )
        except httpx.RequestError as exc:
            raise click.ClickException(
                f"Could not connect to {self.base_url}: {exc}"
            ) from exc

        if response.is_error:
            try:
                body = response.json()
                detail = body.get("detail", body) if isinstance(body, dict) else body
            except ValueError:
                detail = response.text or response.reason_phrase
            raise click.ClickException(
                f"API request failed ({response.status_code}): {detail}"
            )

        if response.status_code == 204:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise click.ClickException("API returned an invalid JSON response") from exc


@dataclass(frozen=True)
class CLIContext:
    client: APIClient
    json_output: bool = False

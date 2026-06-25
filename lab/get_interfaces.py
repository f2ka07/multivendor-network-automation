#!/usr/bin/env python3
"""RESTCONF GET interfaces using credentials from lab/.env only."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def main() -> int:
    lab_dir = Path(__file__).resolve().parent
    load_dotenv(lab_dir / ".env")

    host = os.environ.get("DEVNET_HOST")
    user = os.environ.get("DEVNET_USER")
    password = os.environ.get("DEVNET_PASS")
    port = os.environ.get("DEVNET_RESTCONF_PORT", "443")

    if not all([host, user, password]):
        print("Fill DEVNET_HOST, DEVNET_USER, DEVNET_PASS in lab/.env", file=sys.stderr)
        return 1

    base = f"https://{host}" if port == "443" else f"https://{host}:{port}"
    headers = {"Accept": "application/yang-data+json"}

    response = requests.get(
        f"{base}/restconf/data/ietf-interfaces:interfaces",
        auth=HTTPBasicAuth(user, password),
        headers=headers,
        verify=False,
        timeout=30,
    )
    response.raise_for_status()
    print(response.json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

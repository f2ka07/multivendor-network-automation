#!/usr/bin/env python3
"""RESTCONF GET interfaces using credentials from lab/.env only."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import socket

import requests
from requests.auth import HTTPBasicAuth
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


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

    host = os.environ.get("DEVNET_HOST", "").strip()
    if ":" in host:
        host_part, _, port_part = host.partition(":")
        if port_part.isdigit():
            host = host_part
            os.environ.setdefault("DEVNET_SSH_PORT", port_part)
    user = os.environ.get("DEVNET_USER")
    password = os.environ.get("DEVNET_PASS")
    port = os.environ.get("DEVNET_RESTCONF_PORT", "443")

    if not all([host, user, password]):
        print("Fill DEVNET_HOST, DEVNET_USER, DEVNET_PASS in lab/.env", file=sys.stderr)
        return 1

    try:
        socket.getaddrinfo(host, int(port), type=socket.SOCK_STREAM)
    except socket.gaierror:
        print(
            f"Cannot resolve DEVNET_HOST={host!r} — DNS lookup failed.\n"
            "Copy host, user, and password from the DevNet sandbox portal Quick Access\n"
            "(after Launch). Do not use example hostnames from docs or chat.\n"
            "Known valid patterns: sandbox-iosxe-recomm-1.cisco.com,\n"
            "sandbox-iosxe-latest-1.cisco.com, devnetsandboxiosxe.cisco.com",
            file=sys.stderr,
        )
        return 1

    base = f"https://{host}" if port == "443" else f"https://{host}:{port}"
    headers = {"Accept": "application/yang-data+json"}

    try:
        response = requests.get(
            f"{base}/restconf/data/ietf-interfaces:interfaces",
            auth=HTTPBasicAuth(user, password),
            headers=headers,
            verify=False,
            timeout=30,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError as exc:
        print(
            f"Connection failed to {host}:{port} — {exc}\n"
            "Check DEVNET_HOST in lab/.env matches the portal Quick Access panel.",
            file=sys.stderr,
        )
        return 1
    except requests.exceptions.HTTPError as exc:
        print(
            f"RESTCONF request failed ({exc.response.status_code}) — "
            "credentials may be wrong or expired. Re-launch the sandbox in the\n"
            "DevNet portal and update DEVNET_USER / DEVNET_PASS in lab/.env.",
            file=sys.stderr,
        )
        return 1

    print(response.json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

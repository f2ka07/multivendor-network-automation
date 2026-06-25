#!/usr/bin/env python3
"""NETCONF GET interfaces using credentials from lab/.env (IOS XE DevNet or similar)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from ncclient import manager
from ncclient.transport.errors import AuthenticationError, SessionCloseError, SSHError

INTERFACES_FILTER = """
<interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces"/>
""".strip()


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def parse_host(raw: str) -> str:
    host = raw.strip()
    if ":" in host:
        host_part, _, port_part = host.partition(":")
        if port_part.isdigit():
            os.environ.setdefault("DEVNET_SSH_PORT", port_part)
            return host_part
    return host


def main() -> int:
    lab_dir = Path(__file__).resolve().parent
    load_dotenv(lab_dir / ".env")

    host = parse_host(os.environ.get("DEVNET_HOST", ""))
    user = os.environ.get("DEVNET_USER")
    password = os.environ.get("DEVNET_PASS")
    port = int(os.environ.get("DEVNET_NETCONF_PORT", "830"))

    if not all([host, user, password]):
        print("Fill DEVNET_HOST, DEVNET_USER, DEVNET_PASS in lab/.env", file=sys.stderr)
        return 1

    try:
        with manager.connect(
            host=host,
            port=port,
            username=user,
            password=password,
            hostkey_verify=False,
            allow_agent=False,
            look_for_keys=False,
            device_params={"name": "iosxe"},
            timeout=30,
        ) as session:
            response = session.get(filter=("subtree", INTERFACES_FILTER))
    except AuthenticationError:
        print(
            "NETCONF authentication failed — check DEVNET_USER / DEVNET_PASS in lab/.env.\n"
            "Reservation CAT8Kv (10.10.20.48): connect VPN first; try developer / C1sco12345.",
            file=sys.stderr,
        )
        return 1
    except (SSHError, SessionCloseError, OSError) as exc:
        print(
            f"NETCONF connection failed to {host}:{port} — {exc}\n"
            "DevNet reservation labs require VPN before using 10.10.20.x addresses.",
            file=sys.stderr,
        )
        return 1

    print(response.xml)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

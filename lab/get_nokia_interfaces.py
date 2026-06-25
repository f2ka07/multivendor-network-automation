#!/usr/bin/env python3
"""gNMI GET OpenConfig interfaces from a Nokia SR Linux node (Containerlab)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from pygnmi.client import gNMIclient


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def load_inventory_host(inventory: Path, node: str) -> str | None:
    if not inventory.is_file():
        return None

    current: str | None = None
    hosts: dict[str, dict[str, str]] = {}
    for line in inventory.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.strip() == "---":
            continue
        if not line.startswith(" "):
            current = line.rstrip(":").strip()
            hosts[current] = {}
            continue
        if current and ":" in line:
            key, value = line.strip().split(":", 1)
            hosts[current][key.strip()] = value.strip()

    if node in hosts:
        return hosts[node].get("hostname")
    for name, data in hosts.items():
        if "srl" in data.get("platform", "") or "nokia" in name.lower():
            return data.get("hostname")
    return None


def main() -> int:
    lab_dir = Path(__file__).resolve().parent
    repo_root = lab_dir.parent
    load_dotenv(lab_dir / ".env")

    node = os.environ.get("NOKIA_NODE", "spine")
    inventory = Path(os.environ.get("INVENTORY_FILE", repo_root / "inventory" / "hosts.yaml"))
    user = os.environ.get("NOKIA_USER", "admin")
    password = os.environ.get("NOKIA_PASS", "NokiaSrl1!")
    port = int(os.environ.get("NOKIA_GNMI_PORT", "57400"))

    host = os.environ.get("NOKIA_MGMT_HOST") or load_inventory_host(inventory, node)
    if not host:
        print(
            f"No mgmt address for node {node!r}.\n"
            "Run: LAB_MODE=containerlab ./lab/lab-up.sh\n"
            "Or set NOKIA_MGMT_HOST in lab/.env.",
            file=sys.stderr,
        )
        return 1

    path = ["/interfaces/interface"]
    try:
        with gNMIclient(
            target=(host, port),
            attribute=(user, password),
            override="ip",
            skip_verify=True,
        ) as gc:
            result = gc.get(path=path, encoding="json")
    except Exception as exc:
        print(
            f"gNMI GET failed for {host}:{port} — {exc}\n"
            "Ensure Containerlab is up and the node has finished booting (~30s after deploy).",
            file=sys.stderr,
        )
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

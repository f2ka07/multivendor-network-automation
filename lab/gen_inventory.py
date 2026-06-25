#!/usr/bin/env python3
"""Build Nornir inventory/hosts.yaml from containerlab inspect JSON."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def platform_for(name: str) -> str:
    lower = name.lower()
    if "srl" in lower or "nokia" in lower:
        return "nokia_srlinux"
    if "iol" in lower or "cisco" in lower or "xrd" in lower:
        return "cisco_ios"
    return "linux"


def extract_containers(data: object) -> list[dict]:
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []

    if "containers" in data and isinstance(data["containers"], list):
        return data["containers"]
    if "nodes" in data and isinstance(data["nodes"], list):
        return data["nodes"]

    # containerlab inspect -f json groups nodes by lab name:
    # {"multivendor-intro": [{...}, {...}]}
    containers: list[dict] = []
    for value in data.values():
        if isinstance(value, list):
            containers.extend(item for item in value if isinstance(item, dict))
    return containers


def mgmt_ip(item: dict) -> str:
    raw = item.get("ipv4_address") or item.get("mgmt_ip") or item.get("name") or ""
    return str(raw).split("/")[0].strip()


def short_name(container_name: str) -> str:
    # clab-multivendor-intro-nokia-spine -> spine
    if "-" in container_name:
        return container_name.rsplit("-", 1)[-1]
    return container_name


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: gen_inventory.py <inspect.json>", file=sys.stderr)
        return 1

    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    containers = extract_containers(data)

    nokia_user = os.environ.get("NOKIA_USER", "admin")
    nokia_pass = os.environ.get("NOKIA_PASS", "NokiaSrl1!")
    cisco_user = os.environ.get("CISCO_USER", "admin")
    cisco_pass = os.environ.get("CISCO_PASS", "admin")

    lines = ["---"]
    for item in containers:
        name = item.get("name") or item.get("container_name")
        if not name:
            continue
        short = short_name(name)
        host = mgmt_ip(item)
        plat = platform_for(name)
        if plat == "nokia_srlinux":
            user, password = nokia_user, nokia_pass
        elif plat == "cisco_ios":
            user, password = cisco_user, cisco_pass
        else:
            user, password = "root", "root"

        lines.append(f"{short}:")
        lines.append(f"  hostname: {host}")
        lines.append(f"  platform: {plat}")
        lines.append(f"  username: {user}")
        lines.append(f"  password: {password}")
        lines.append("  port: 22")
        lines.append("")

    sys.stdout.write("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

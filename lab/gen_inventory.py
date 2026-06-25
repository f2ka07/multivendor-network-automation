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


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: gen_inventory.py <inspect.json>", file=sys.stderr)
        return 1

    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    containers = data.get("containers") or data.get("nodes") or []

    nokia_user = os.environ.get("NOKIA_USER", "admin")
    nokia_pass = os.environ.get("NOKIA_PASS", "NokiaSrl1!")
    cisco_user = os.environ.get("CISCO_USER", "admin")
    cisco_pass = os.environ.get("CISCO_PASS", "admin")

    lines = ["---"]
    for item in containers:
        name = item.get("name") or item.get("container_name")
        if not name:
            continue
        short = name.split("-")[-1] if "-" in name else name
        host = item.get("ipv4_address") or item.get("mgmt_ip") or name
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

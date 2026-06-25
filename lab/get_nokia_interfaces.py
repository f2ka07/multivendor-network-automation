#!/usr/bin/env python3
"""gNMI GET OpenConfig interfaces from a Nokia SR Linux node (Containerlab)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from pygnmi.client import gNMIclient

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_inventory import extract_containers, mgmt_ip, platform_for, short_name


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def resolve_inventory_path(raw: str | None, repo_root: Path) -> Path:
    if not raw:
        return repo_root / "inventory" / "hosts.yaml"
    path = Path(raw)
    if path.is_absolute():
        return path
    return repo_root / path


def resolve_topology_path(repo_root: Path) -> Path:
    raw = os.environ.get("TOPOLOGY_FILE", "lab/topology.clab.yml")
    path = Path(raw)
    if path.is_absolute():
        return path
    return repo_root / path


def load_inventory_hosts(inventory: Path) -> dict[str, dict[str, str]]:
    hosts: dict[str, dict[str, str]] = {}
    if not inventory.is_file():
        return hosts

    current: str | None = None
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
    return hosts


def hosts_from_inspect(data: object) -> dict[str, dict[str, str]]:
    hosts: dict[str, dict[str, str]] = {}
    for item in extract_containers(data):
        name = item.get("name") or item.get("container_name") or ""
        if not name or platform_for(name) != "nokia_srlinux":
            continue
        short = short_name(name)
        hosts[short] = {
            "hostname": mgmt_ip(item),
            "platform": "nokia_srlinux",
        }
    return hosts


def hosts_from_containerlab(topo: Path) -> dict[str, dict[str, str]]:
    if not topo.is_file():
        return {}

    for cmd in (
        ["containerlab", "inspect", "-t", str(topo), "--format", "json"],
        ["sudo", "containerlab", "inspect", "-t", str(topo), "--format", "json"],
    ):
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0 or not proc.stdout.strip():
            continue
        try:
            hosts = hosts_from_inspect(json.loads(proc.stdout))
        except json.JSONDecodeError:
            continue
        if hosts:
            return hosts
    return {}


def pick_host(hosts: dict[str, dict[str, str]], node: str) -> tuple[str | None, str | None]:
    if node in hosts:
        data = hosts[node]
        if data.get("platform") == "nokia_srlinux":
            return data.get("hostname"), node

    for name, data in hosts.items():
        if data.get("platform") != "nokia_srlinux":
            continue
        if name == node or name.endswith(f"-{node}"):
            return data.get("hostname"), name

    for name, data in hosts.items():
        if data.get("platform") == "nokia_srlinux":
            return data.get("hostname"), name

    return None, None


def nokia_nodes(hosts: dict[str, dict[str, str]]) -> dict[str, str]:
    return {
        name: data["hostname"]
        for name, data in hosts.items()
        if data.get("platform") == "nokia_srlinux" and data.get("hostname")
    }


def node_for_ip(hosts: dict[str, dict[str, str]], ip: str) -> tuple[str | None, dict[str, str]]:
    for name, data in hosts.items():
        if data.get("hostname") == ip:
            return name, data
    return None, {}


def gnmi_get(host: str, port: int, user: str, password: str, paths: list[str]) -> object:
    """Connect with skip_verify; fall back to insecure for containerlab self-signed certs."""
    errors: list[str] = []
    for kwargs in (
        {"skip_verify": True},
        {"insecure": True},
    ):
        try:
            with gNMIclient(
                target=(host, str(port)),
                username=user,
                password=password,
                **kwargs,
            ) as gc:
                return gc.get(path=paths, encoding="json")
        except Exception as exc:
            errors.append(f"{kwargs}: {exc!r}")
    raise RuntimeError("; ".join(errors))


def main() -> int:
    lab_dir = Path(__file__).resolve().parent
    repo_root = lab_dir.parent
    load_dotenv(lab_dir / ".env")

    node = os.environ.get("NOKIA_NODE", "spine")
    inventory = resolve_inventory_path(os.environ.get("INVENTORY_FILE"), repo_root)
    user = os.environ.get("NOKIA_USER", "admin")
    password = os.environ.get("NOKIA_PASS", "NokiaSrl1!")
    port = int(os.environ.get("NOKIA_GNMI_PORT", "57400"))

    hosts = load_inventory_hosts(inventory)
    if not hosts:
        hosts = hosts_from_containerlab(resolve_topology_path(repo_root))
    elif not nokia_nodes(hosts):
        hosts.update(hosts_from_containerlab(resolve_topology_path(repo_root)))

    host = os.environ.get("NOKIA_MGMT_HOST")
    matched_node = node
    if not host:
        host, matched_node = pick_host(hosts, node)
    else:
        ip_name, ip_data = node_for_ip(hosts, host)
        if ip_data and ip_data.get("platform") != "nokia_srlinux":
            nokia = nokia_nodes(hosts)
            print(
                f"NOKIA_MGMT_HOST={host} is {ip_name!r} (not Nokia). "
                f"Using Nokia node instead: {nokia}",
                file=sys.stderr,
            )
            host, matched_node = pick_host(hosts, node)

    if not host:
        available = ", ".join(sorted(hosts)) or "(no Nokia nodes found)"
        print(
            f"No mgmt address for node {node!r}.\n"
            f"Inventory: {inventory} ({'missing' if not inventory.is_file() else 'empty or stale'})\n"
            f"Available nodes: {available}\n"
            "1. LAB_MODE=containerlab ./lab/lab-up.sh\n"
            "2. sudo containerlab inspect -t lab/topology.clab.yml\n"
            "3. Or set NOKIA_MGMT_HOST=172.20.20.x in lab/.env",
            file=sys.stderr,
        )
        return 1

    if matched_node and matched_node != node:
        print(f"Using inventory node {matched_node!r} -> {host}", file=sys.stderr)
    else:
        print(f"Connecting gNMI to {matched_node or node!r} at {host}:{port}", file=sys.stderr)

    paths = [
        "openconfig-interfaces:interfaces",
        "/interfaces/interface",
    ]
    try:
        result = gnmi_get(host, port, user, password, paths)
    except Exception as exc:
        nokia_ips = nokia_nodes(hosts)
        print(
            f"gNMI GET failed for {host}:{port} — {exc}\n"
            f"Nokia nodes in inventory: {nokia_ips or 'none'}\n"
            "172.20.20.4 is usually linux-host, not Nokia — use spine/leaf IP from:\n"
            "  sudo containerlab inspect -t lab/topology.clab.yml\n"
            "Set NOKIA_NODE=spine or NOKIA_MGMT_HOST=<nokia-spine-ip> in lab/.env.\n"
            "Wait ~60s after deploy for SR Linux gNMI to start.",
            file=sys.stderr,
        )
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env bash
# Deploy or validate the lab. Students only need a filled lab/.env file.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${LAB_ENV_FILE:-$SCRIPT_DIR/.env}"

die() { echo "ERROR: $*" >&2; exit 1; }

if [[ ! -f "$ENV_FILE" ]]; then
  die "Missing $ENV_FILE — copy lab/.env.example to lab/.env and add credentials."
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

# Export for child processes (Python scripts read os.environ)
export DEVNET_HOST DEVNET_USER DEVNET_PASS
export DEVNET_SSH_PORT DEVNET_NETCONF_PORT DEVNET_RESTCONF_PORT
export NETBOX_URL NETBOX_TOKEN LAB_MODE

LAB_MODE="${LAB_MODE:-devnet}"
export NOKIA_USER NOKIA_PASS CISCO_USER CISCO_PASS

lab_up_devnet() {
  : "${DEVNET_HOST:?Set DEVNET_HOST in lab/.env}"
  : "${DEVNET_USER:?Set DEVNET_USER in lab/.env}"
  : "${DEVNET_PASS:?Set DEVNET_PASS in lab/.env}"

  echo "==> DevNet lab ready (credentials loaded from lab/.env)"
  echo "    Host:     $DEVNET_HOST"
  echo "    User:     $DEVNET_USER"
  echo "    SSH:      ${DEVNET_SSH_PORT:-22}"
  echo "    NETCONF:  ${DEVNET_NETCONF_PORT:-830}"
  echo "    RESTCONF: ${DEVNET_RESTCONF_PORT:-443}"
  echo ""
  echo "Next:"
  echo "  python lab/get_interfaces.py          # RESTCONF"
  echo "  python lab/get_interfaces_netconf.py  # NETCONF (port ${DEVNET_NETCONF_PORT:-830})"
}

lab_up_containerlab() {
  command -v containerlab >/dev/null 2>&1 || die "containerlab not installed — run: bash lab/bootstrap.sh"
  docker info >/dev/null 2>&1 || die "Docker not running — start Docker Desktop (WSL) or: sudo systemctl start docker"

  TOPO="${TOPOLOGY_FILE:-$SCRIPT_DIR/topology.clab.yml}"
  [[ -f "$TOPO" ]] || die "Topology not found: $TOPO"

  INSPECT_JSON="$(mktemp)"
  INV_OUT="${INVENTORY_FILE:-$REPO_ROOT/inventory/hosts.yaml}"

  echo "==> Pulling Nokia SR Linux image (if needed)..."
  docker pull ghcr.io/nokia/srlinux:latest >/dev/null 2>&1 || true

  echo "==> Deploying Containerlab topology: $TOPO"
  sudo containerlab deploy -t "$TOPO" --reconfigure

  echo "==> Waiting for nodes to boot (30s)..."
  sleep 30

  echo "==> Generating Nornir inventory..."
  mkdir -p "$(dirname "$INV_OUT")"
  sudo containerlab inspect -t "$TOPO" --format json > "$INSPECT_JSON"
  python3 "$SCRIPT_DIR/gen_inventory.py" "$INSPECT_JSON" > "$INV_OUT"
  rm -f "$INSPECT_JSON"

  echo "==> Containerlab lab ready"
  sudo containerlab inspect -t "$TOPO"
  echo ""
  echo "    Inventory: $INV_OUT"
  echo "Next:"
  echo "  python lab/get_nokia_interfaces.py    # gNMI (node: \${NOKIA_NODE:-spine})"
  echo "  cat $INV_OUT"
}

case "$LAB_MODE" in
  devnet) lab_up_devnet ;;
  containerlab) lab_up_containerlab ;;
  *) die "Unknown LAB_MODE=$LAB_MODE (use devnet or containerlab)" ;;
esac

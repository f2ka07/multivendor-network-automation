#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${LAB_ENV_FILE:-$SCRIPT_DIR/.env}"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

LAB_MODE="${LAB_MODE:-devnet}"

if [[ "$LAB_MODE" != "containerlab" ]]; then
  echo "DevNet mode: nothing to tear down. Clear lab/.env when sandbox expires."
  exit 0
fi

TOPO="${TOPOLOGY_FILE:-$SCRIPT_DIR/topology.clab.yml}"
echo "==> Destroying Containerlab topology: $TOPO"
sudo containerlab destroy -t "$TOPO" --cleanup
echo "Done."

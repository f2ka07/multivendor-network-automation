#!/usr/bin/env bash
# Quick validation that self-lab prerequisites are met.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ok() { echo "[OK] $*"; }
fail() { echo "[FAIL] $*" >&2; ERR=1; }

ERR=0

if grep -qiE 'microsoft|WSL' /proc/version 2>/dev/null; then
  ok "WSL2 detected"
else
  ok "Native Linux detected"
fi

if docker info >/dev/null 2>&1; then
  ok "Docker daemon running"
else
  fail "Docker not running"
fi

if command -v containerlab >/dev/null 2>&1; then
  ok "Containerlab installed"
else
  fail "Containerlab missing — run: bash lab/bootstrap.sh"
fi

if docker image inspect ghcr.io/nokia/srlinux:latest >/dev/null 2>&1; then
  ok "Nokia SR Linux image present"
else
  fail "Nokia image missing — run: docker pull ghcr.io/nokia/srlinux:latest"
fi

if [[ -d "$REPO_ROOT/venv" ]]; then
  ok "Python venv exists"
else
  fail "venv missing — run: bash lab/bootstrap.sh"
fi

if [[ -f "$SCRIPT_DIR/.env" ]]; then
  ok "lab/.env present"
else
  fail "lab/.env missing — cp lab/.env.example lab/.env"
fi

if [[ "${ERR:-0}" -eq 0 ]]; then
  echo "All checks passed. Run: ./lab/lab-up.sh"
else
  echo "Fix failures above, then re-run: bash lab/check-prereqs.sh"
  exit 1
fi

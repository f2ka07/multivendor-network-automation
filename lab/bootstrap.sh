#!/usr/bin/env bash
# One-time machine setup: WSL2 (Docker Desktop), student-owned EC2, or native Linux.
# Each student provisions their own lab host. No shared instructor infrastructure.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

die() { echo "ERROR: $*" >&2; exit 1; }
info() { echo "==> $*"; }

is_wsl() {
  grep -qiE 'microsoft|WSL' /proc/version 2>/dev/null
}

is_root() { [[ "${EUID:-$(id -u)}" -eq 0 ]]; }

install_linux_packages() {
  if is_wsl; then
    info "WSL detected — use Docker Desktop on Windows (WSL integration enabled)."
    info "Skipping apt/docker install inside WSL."
    return 0
  fi

  if ! is_root; then
    die "On Linux/EC2 run: sudo bash lab/bootstrap.sh"
  fi

  export DEBIAN_FRONTEND=noninteractive
  info "Installing system packages (Ubuntu/Debian)..."
  apt-get update
  apt-get install -y git python3 python3-venv python3-pip curl jq ca-certificates

  if ! command -v docker >/dev/null 2>&1; then
    info "Installing Docker..."
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sh /tmp/get-docker.sh
  fi

  if id ubuntu &>/dev/null; then
    usermod -aG docker ubuntu || true
  elif [[ -n "${SUDO_USER:-}" ]]; then
    usermod -aG docker "$SUDO_USER" || true
  fi

  info "Log out and back in (or new SSH session) so docker group membership applies."
}

ensure_docker() {
  if docker info >/dev/null 2>&1; then
    info "Docker daemon is running."
    return 0
  fi
  if is_wsl; then
    die "Start Docker Desktop on Windows and enable Settings → Resources → WSL integration → your Ubuntu distro."
  fi
  die "Docker is not running. Start the service: sudo systemctl start docker"
}

ensure_containerlab() {
  if command -v containerlab >/dev/null 2>&1; then
    info "Containerlab already installed: $(containerlab version 2>/dev/null | head -1 || true)"
    return 0
  fi

  local install_url="https://get.containerlab.dev"
  info "Installing Containerlab from ${install_url}..."

  local installer
  installer="$(curl -fsSL "$install_url")" || die "Failed to download Containerlab installer from ${install_url}"

  if [[ "${installer:0:1}" == "<" ]]; then
    die "Installer returned HTML (wrong URL or network proxy). Use: bash -c \"\$(curl -fsSL ${install_url})\""
  fi

  # Official install script (deb/rpm); may prompt for sudo password on WSL
  bash -c "$installer"

  command -v containerlab >/dev/null 2>&1 || die "Containerlab install finished but 'containerlab' not in PATH"
  info "Containerlab installed: $(containerlab version 2>/dev/null | head -1 || true)"
}

pull_images() {
  info "Pulling Nokia SR Linux image (free, no license)..."
  docker pull ghcr.io/nokia/srlinux:latest
  docker pull alpine:latest >/dev/null 2>&1 || true
}

setup_python_venv() {
  local venv="$REPO_ROOT/venv"
  if [[ -d "$venv" ]]; then
    info "Python venv already exists at $venv"
    return 0
  fi
  info "Creating Python venv and installing lab dependencies..."
  python3 -m venv "$venv"
  # shellcheck disable=SC1091
  source "$venv/bin/activate"
  pip install --upgrade pip
  pip install -r "$SCRIPT_DIR/requirements.txt"
  info "Activate later with: source venv/bin/activate"
}

make_scripts_executable() {
  chmod +x "$SCRIPT_DIR"/lab-up.sh "$SCRIPT_DIR"/lab-down.sh "$SCRIPT_DIR"/bootstrap.sh
  chmod +x "$SCRIPT_DIR"/wsl-bootstrap.sh "$SCRIPT_DIR"/ec2-bootstrap.sh "$SCRIPT_DIR"/check-prereqs.sh 2>/dev/null || true
  chmod +x "$SCRIPT_DIR"/gen_inventory.py "$SCRIPT_DIR"/get_interfaces.py \
    "$SCRIPT_DIR"/get_interfaces_netconf.py "$SCRIPT_DIR"/get_nokia_interfaces.py 2>/dev/null || true
}

print_next_steps() {
  cat <<EOF

Bootstrap complete (self-hosted lab).

Repo:  $REPO_ROOT
Clone: https://github.com/f2ka07/multivendor-network-automation

Next (every lab session):
  cd $REPO_ROOT
  cp lab/.env.example lab/.env    # paste DevNet creds; set LAB_MODE=containerlab for local NOS
  ./lab/lab-up.sh
  source venv/bin/activate
  python lab/get_interfaces.py          # DevNet RESTCONF
  python lab/get_interfaces_netconf.py  # DevNet NETCONF
  python lab/get_nokia_interfaces.py    # Containerlab gNMI
  ./lab/lab-down.sh               # when using LAB_MODE=containerlab

WSL2: keep the repo under ~/ (not /mnt/c/). Allocate 8GB+ RAM in .wslconfig for Containerlab.
EOF
}

main() {
  info "Self-lab bootstrap — each student owns this machine (WSL2 or personal EC2)."
  install_linux_packages
  ensure_docker
  ensure_containerlab
  pull_images
  setup_python_venv
  make_scripts_executable
  print_next_steps
}

main "$@"

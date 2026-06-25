#!/usr/bin/env bash
# Run once on a fresh Ubuntu 22.04 EC2 instance (instructor / cloud-init).
# After this, students only SSH in and edit lab/.env.
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

REPO_URL="${LAB_REPO_URL:-https://github.com/f2ka07/multivendor-network-automation.git}"
REPO_DIR="${LAB_REPO_DIR:-/opt/multivendor-network-automation}"

apt-get update
apt-get upgrade -y
apt-get install -y git python3 python3-venv python3-pip curl jq

curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
sh /tmp/get-docker.sh
usermod -aG docker ubuntu 2>/dev/null || usermod -aG docker "$SUDO_USER" 2>/dev/null || true

curl -sL https://containerlab.dev | bash

docker pull ghcr.io/nokia/srlinux:latest

if [[ ! -d "$REPO_DIR/.git" ]]; then
  git clone "$REPO_URL" "$REPO_DIR"
else
  git -C "$REPO_DIR" pull --ff-only || true
fi

chmod +x "$REPO_DIR"/lab/lab-up.sh
chmod +x "$REPO_DIR"/lab/lab-down.sh

echo "Bootstrap complete."
echo "  Repo:    $REPO_URL"
echo "  Path:    $REPO_DIR"
echo "  Docker and Containerlab installed"
echo "  Nokia SR Linux image pulled"
echo "  Students: cd $REPO_DIR && cp lab/.env.example lab/.env && ./lab/lab-up.sh"

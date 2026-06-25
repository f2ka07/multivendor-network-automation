#!/usr/bin/env bash
# Deprecated name — use lab/bootstrap.sh (same script, any self-hosted Linux/WSL2/EC2).
exec "$(dirname "$0")/bootstrap.sh" "$@"

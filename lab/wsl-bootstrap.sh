#!/usr/bin/env bash
# WSL2 entry point — same as bootstrap.sh (self-hosted student lab).
exec "$(dirname "$0")/bootstrap.sh" "$@"

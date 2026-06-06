#!/usr/bin/env bash
# Instagram Manager — Approve entry point
set -euo pipefail
exec python -m instagram_manager approve "$@"

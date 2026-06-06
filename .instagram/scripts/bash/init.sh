#!/usr/bin/env bash
# Instagram Manager — Init entry point
set -euo pipefail
exec python -m instagram_manager init "$@"

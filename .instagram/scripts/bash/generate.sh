#!/usr/bin/env bash
# Instagram Manager — Generate entry point
set -euo pipefail
exec python -m instagram_manager generate "$@"

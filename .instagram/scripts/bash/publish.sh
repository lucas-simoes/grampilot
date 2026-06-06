#!/usr/bin/env bash
# Instagram Manager — Publish entry point
set -euo pipefail
exec python -m instagram_manager publish "$@"

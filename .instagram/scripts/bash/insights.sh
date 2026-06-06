#!/usr/bin/env bash
# Instagram Manager — Insights entry point
set -euo pipefail
exec python -m instagram_manager insights "$@"

#!/usr/bin/env bash
# Instagram Manager — Media entry point
set -euo pipefail
exec python -m instagram_manager media "$@"

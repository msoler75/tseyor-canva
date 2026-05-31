#!/bin/bash
# tc_render.sh — Simple wrapper for tc_render.js
#
# Usage:
#   ./scripts/smart-import/tc_render.sh <input.tc> <output.png>
#
# Examples:
#   ./scripts/smart-import/tc_render.sh output/gemini-2.5-flash/img-01/design.tc output/gemini-2.5-flash/img-01/render.png
#   ./scripts/smart-import/tc_render.sh --tc path/to/design.tc --output path/to/render.png
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ $# -eq 2 ]; then
  # Positional args: tc_render.sh <tc> <output>
  exec node "$SCRIPT_DIR/tc_render.js" --tc "$1" --output "$2"
elif [ $# -ge 2 ]; then
  # Named args: pass through
  exec node "$SCRIPT_DIR/tc_render.js" "$@"
else
  echo "Usage: $0 [--tc] <input.tc> [--output] <output.png>"
  echo ""
  echo "Examples:"
  echo "  $0 design.tc render.png"
  echo "  $0 --tc design.tc --output render.png"
  exit 1
fi

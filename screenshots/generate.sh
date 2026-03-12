#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$HOME/.local/lib/omarchy-monitor-arrange/.venv/bin/python"
OUT_DIR="$SCRIPT_DIR/svg"

if ! command -v shellfie &>/dev/null; then
  echo "Error: shellfie-cli not found. Install with: npm install -g shellfie-cli" >&2
  exit 1
fi

if [[ ! -x "$VENV_PYTHON" ]]; then
  VENV_PYTHON=python3
fi

echo "==> Capturing app states as ANSI..."
PYTHONPATH="$PROJECT_DIR/src" "$VENV_PYTHON" "$SCRIPT_DIR/capture.py"

mkdir -p "$OUT_DIR"

SHELLFIE_OPTS=(
  -t minimal
  --no-controls
  --no-highlight
  --embed-font
  --font-size 13
  --line-height 1.3
  -T tokyoNight
)

declare -A TITLES=(
  [main]="Monitor Arrange — Main View"
  [select-dp2]="Monitor Arrange — DP-2 Selected"
  [select-edp1]="Monitor Arrange — Primary (eDP-1)"
  [help]="Monitor Arrange — Help Overlay"
)

echo "==> Generating SVGs with shellfie..."
for ansi_file in "$SCRIPT_DIR"/*.ansi; do
  name="$(basename "$ansi_file" .ansi)"
  title="${TITLES[$name]:-$name}"
  out="$OUT_DIR/$name.svg"
  shellfie "$ansi_file" "${SHELLFIE_OPTS[@]}" -i "$title" -o "$out"
  echo "  $out"
done

echo ""
echo "==> Done! SVGs are in $OUT_DIR/"

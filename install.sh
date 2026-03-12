#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
LIB_DIR="$HOME/.local/lib/omarchy-monitor-arrange"
BIN_DIR="$HOME/.local/bin"
LAUNCHER="$BIN_DIR/omarchy-monitor-arrange"
OMARCHY_BIN="$HOME/.local/share/omarchy/bin"
OMARCHY_LINK="$OMARCHY_BIN/omarchy-monitor-arrange"
HYPR_CONF="$HOME/.config/hypr/hyprland.conf"
BINDINGS_CONF="$HOME/.config/hypr/bindings.conf"

uninstall() {
  echo "==> Uninstalling omarchy-monitor-arrange"

  # Remove library
  if [[ -d "$LIB_DIR" ]]; then
    echo "  Removing $LIB_DIR ..."
    rm -rf "$LIB_DIR"
  fi

  # Remove symlink from omarchy bin
  if [[ -L "$OMARCHY_LINK" ]]; then
    echo "  Removing symlink $OMARCHY_LINK ..."
    rm -f "$OMARCHY_LINK"
  fi

  # Remove launcher
  if [[ -f "$LAUNCHER" ]]; then
    echo "  Removing $LAUNCHER ..."
    rm -f "$LAUNCHER"
  fi

  # Remove window rule from hyprland.conf
  if [[ -f "$HYPR_CONF" ]] && grep -qF 'org.omarchy.omarchy-monitor-arrange' "$HYPR_CONF"; then
    echo "  Removing window rule from $HYPR_CONF ..."
    sed -i '/org\.omarchy\.omarchy-monitor-arrange/d' "$HYPR_CONF"
  fi

  # Remove keybinding from bindings.conf
  if [[ -f "$BINDINGS_CONF" ]] && grep -qF 'omarchy-monitor-arrange' "$BINDINGS_CONF"; then
    echo "  Removing keybinding from $BINDINGS_CONF ..."
    sed -i '/omarchy-monitor-arrange/d' "$BINDINGS_CONF"
  fi

  echo ""
  echo "==> Uninstall complete."
}

install() {
  echo "==> Installing omarchy-monitor-arrange"

  # 1. Copy library
  echo "  Copying library to $LIB_DIR ..."
  mkdir -p "$LIB_DIR"
  rm -rf "$LIB_DIR/omarchy_monitor_arrange"
  cp -r "$PROJECT_DIR/src/omarchy_monitor_arrange" "$LIB_DIR/"

  # 2. Set up venv and install dependencies
  VENV_DIR="$LIB_DIR/.venv"
  if [[ ! -d "$VENV_DIR" ]]; then
    echo "  Creating virtual environment in $VENV_DIR ..."
    /usr/bin/python3 -m venv "$VENV_DIR"
  fi
  echo "  Installing Python dependencies ..."
  "$VENV_DIR/bin/pip" install --quiet -r "$PROJECT_DIR/requirements.txt"

  # 3. Install launcher
  echo "  Installing launcher to $LAUNCHER ..."
  mkdir -p "$BIN_DIR"
  cp "$PROJECT_DIR/bin/omarchy-monitor-arrange" "$LAUNCHER"
  chmod +x "$LAUNCHER"

  # 4. Symlink into omarchy bin dir (which is on PATH)
  if [[ -d "$OMARCHY_BIN" ]]; then
    echo "  Symlinking into $OMARCHY_BIN ..."
    ln -sf "$LAUNCHER" "$OMARCHY_LINK"
  fi

  # 5. Add Hyprland window rule (idempotent)
  if [[ -f "$HYPR_CONF" ]]; then
    if ! grep -qF 'org.omarchy.omarchy-monitor-arrange' "$HYPR_CONF"; then
      echo "  Adding window rule to $HYPR_CONF ..."
      printf '\n%s\n' 'windowrule = tag +floating-window, match:class org.omarchy.omarchy-monitor-arrange' >> "$HYPR_CONF"
    else
      echo "  Window rule already present in $HYPR_CONF (org.omarchy.omarchy-monitor-arrange)"
    fi
  else
    echo "  Skipping window rule ($HYPR_CONF not found)"
  fi

  # 6. Add keybinding SUPER ALT + M (idempotent)
  if [[ -f "$BINDINGS_CONF" ]]; then
    if ! grep -qF 'omarchy-monitor-arrange' "$BINDINGS_CONF"; then
      echo "  Adding keybinding (SUPER ALT + M) to $BINDINGS_CONF ..."
      printf '\n%s\n' 'bindd = SUPER ALT, M, Monitor Arrangement, exec, omarchy-launch-or-focus-tui omarchy-monitor-arrange' >> "$BINDINGS_CONF"
    else
      echo "  Keybinding already present in $BINDINGS_CONF"
    fi
  else
    echo "  Skipping keybinding ($BINDINGS_CONF not found)"
  fi

  echo ""
  echo "==> Done! Run with:"
  echo "    omarchy-monitor-arrange"
  echo "    or press SUPER + ALT + M"
}

case "${1:-}" in
  --uninstall)
    uninstall
    ;;
  --help|-h)
    echo "Usage: ./install.sh [--uninstall]"
    echo ""
    echo "  (no args)     Install omarchy-monitor-arrange"
    echo "  --uninstall   Remove all installed files and config entries"
    ;;
  *)
    install
    ;;
esac

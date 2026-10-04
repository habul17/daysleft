#!/usr/bin/env bash
# Removes Days Left and brings back the wallpaper you had before installing it.
set -euo pipefail

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
DATA_DIR="$DATA_HOME/daysleft"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

echo "==> Removing the midnight timer"
systemctl --user disable --now daysleft.timer daysleft.service 2>/dev/null || true
rm -f "$UNIT_DIR/daysleft.service" "$UNIT_DIR/daysleft.timer"
systemctl --user daemon-reload

echo "==> Restoring your previous wallpaper"
PYTHONPATH="$DATA_DIR/app" python3 -m daysleft restore || true

echo "==> Removing the app"
rm -f "$DATA_HOME/applications/local.daysleft.DaysLeft.desktop" \
      "$DATA_HOME/icons/hicolor/scalable/apps/local.daysleft.DaysLeft.svg"
rm -rf "$DATA_DIR" "${XDG_CONFIG_HOME:-$HOME/.config}/daysleft"
echo "Days Left removed."

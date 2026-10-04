#!/usr/bin/env bash
# Installs Days Left for the current user on GNOME: the app, its settings
# window in the app grid and a systemd timer that refreshes the wallpaper
# every midnight.
# Safe to run again to update an existing install.
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
APP_DIR="$DATA_HOME/daysleft/app"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
APP_ID="local.daysleft.DaysLeft"

if [[ ":${XDG_CURRENT_DESKTOP:-}:" != *":GNOME:"* ]]; then
    echo "Days Left v1 needs a GNOME desktop." >&2
    exit 1
fi
if ! python3 -c 'import gi; gi.require_version("Adw", "1"); import PIL' 2>/dev/null; then
    echo "Missing packages. Install them with: sudo apt install python3-pil python3-gi gir1.2-adw-1" >&2
    exit 1
fi

echo "==> Installing the app to $APP_DIR"
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR"
cp -r "$SRC/daysleft" "$APP_DIR/"
find "$APP_DIR" -name __pycache__ -prune -exec rm -rf {} +
PYTHONPATH="$APP_DIR" python3 -m daysleft backup

echo "==> Adding Days Left to the app grid"
mkdir -p "$DATA_HOME/applications" "$DATA_HOME/icons/hicolor/scalable/apps"
cp "$SRC/data/$APP_ID.svg" "$DATA_HOME/icons/hicolor/scalable/apps/"
cat > "$DATA_HOME/applications/$APP_ID.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Days Left
Comment=Choose how your Days Left wallpaper looks
Exec=env PYTHONPATH=$APP_DIR /usr/bin/python3 -m daysleft settings
Icon=$APP_ID
Categories=Settings;DesktopSettings;GTK;
Keywords=wallpaper;background;year;countdown;
StartupNotify=true
DESKTOP

echo "==> Installing the midnight timer"
mkdir -p "$UNIT_DIR"
cp "$SRC/systemd/daysleft.service" "$SRC/systemd/daysleft.timer" "$UNIT_DIR/"
systemctl --user daemon-reload
systemctl --user enable daysleft.service
systemctl --user enable --now daysleft.timer

echo "==> Setting today's wallpaper"
systemctl --user start daysleft.service
echo "Wallpaper: $(gsettings get org.gnome.desktop.background picture-uri-dark)"

cat <<'EOF'

Done. Open "Days Left" from your app grid to choose how the wallpaper looks.
EOF

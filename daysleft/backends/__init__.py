"""Desktop-specific wallpaper handling.

v1 supports GNOME. Each new desktop (KDE, Windows, macOS, ...) gets its own
module exposing the same functions as gnome.py: screen_size(),
wallpaper_uris(), set_wallpaper(light, dark), save_settings(path) and
restore_settings(path).
"""

import os


def detect():
    desktops = os.environ.get("XDG_CURRENT_DESKTOP", "").upper().split(":")
    if "GNOME" in desktops:
        from . import gnome
        return gnome
    raise SystemExit(f"Unsupported desktop {os.environ.get('XDG_CURRENT_DESKTOP')!r}: "
                     "Days Left v1 supports GNOME only.")

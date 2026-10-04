"""GNOME: reads the screen size from Mutter and sets the wallpaper via GSettings."""

import json
from pathlib import Path

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

BACKGROUND = "org.gnome.desktop.background"
SCREENSAVER = "org.gnome.desktop.screensaver"

# Every setting set_wallpaper() touches, so the previous wallpaper can be restored.
KEYS = [
    (BACKGROUND, "picture-uri"),
    (BACKGROUND, "picture-uri-dark"),
    (BACKGROUND, "picture-options"),
    (SCREENSAVER, "picture-uri"),
]

# Used when Mutter can't be asked (e.g. very early in login); zoom scales it down.
FALLBACK_SIZE = (3840, 2160)


def screen_size() -> tuple[int, int]:
    """Native resolution of the largest active monitor."""
    try:
        reply = Gio.bus_get_sync(Gio.BusType.SESSION).call_sync(
            "org.gnome.Mutter.DisplayConfig", "/org/gnome/Mutter/DisplayConfig",
            "org.gnome.Mutter.DisplayConfig", "GetCurrentState",
            None, None, Gio.DBusCallFlags.NONE, -1, None,
        )
    except GLib.Error:
        return FALLBACK_SIZE
    _serial, monitors, _logical_monitors, _properties = reply.unpack()
    sizes = [
        (mode[1], mode[2])
        for _spec, modes, _monitor_properties in monitors
        for mode in modes
        if mode[6].get("is-current")
    ]
    return max(sizes, key=lambda size: size[0] * size[1], default=FALLBACK_SIZE)


def wallpaper_uris() -> tuple[str, str]:
    """The current (light mode, dark mode) wallpapers."""
    background = Gio.Settings.new(BACKGROUND)
    return background.get_string("picture-uri"), background.get_string("picture-uri-dark")


def set_wallpaper(light: Path, dark: Path) -> None:
    """Sets the wallpaper for light and dark mode; GNOME switches between them."""
    background = Gio.Settings.new(BACKGROUND)
    background.set_string("picture-uri", light.as_uri())
    background.set_string("picture-uri-dark", dark.as_uri())
    background.set_string("picture-options", "zoom")
    Gio.Settings.new(SCREENSAVER).set_string("picture-uri", light.as_uri())
    Gio.Settings.sync()  # flush to dconf before the process exits


def save_settings(path: Path) -> None:
    values = {f"{schema} {key}": Gio.Settings.new(schema).get_string(key) for schema, key in KEYS}
    path.write_text(json.dumps(values, indent=2) + "\n")


def restore_settings(path: Path) -> None:
    values = json.loads(path.read_text())
    for schema, key in KEYS:
        Gio.Settings.new(schema).set_string(key, values[f"{schema} {key}"])
    Gio.Settings.sync()

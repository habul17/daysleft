"""Days Left: a wallpaper showing how many days are left in the year.

  python3 -m daysleft settings            open the settings window
  python3 -m daysleft apply               render today's wallpaper and set it
  python3 -m daysleft preview FILE        render to FILE without setting it
  python3 -m daysleft backup | restore    save / bring back the previous wallpaper
"""

import argparse
import hashlib
import io
from datetime import date
from pathlib import Path

from . import backends, settings as config
from .render import counter, render
from .year import year_status

WALLPAPER_DIR = config.DATA_DIR / "wallpapers"
BACKUP_FILE = config.DATA_DIR / "previous-wallpaper.json"


def apply(today: date) -> None:
    backend = backends.detect()
    settings = config.load()
    status = year_status(today)
    size = backend.screen_size()

    # "Match system" gets a light and a dark wallpaper; GNOME picks one.
    modes = {"system": (False, True), "dark": (True,), "light": (False,)}[settings.theme]
    paths = {dark: _save(render(status, *size, settings, dark), today) for dark in modes}
    light, dark = paths.get(False) or paths[True], paths.get(True) or paths[False]

    if backend.wallpaper_uris() != (light.as_uri(), dark.as_uri()):
        backend.set_wallpaper(light, dark)
        number, caption = counter(status, settings)
        print(f"Wallpaper set: {number} {caption} ({settings.style}, {settings.theme})")

    for old in WALLPAPER_DIR.glob("daysleft-*.png"):
        if old not in (light, dark):
            old.unlink()


def _save(image, today: date) -> Path:
    """Writes the image under a name unique to its content: GNOME only reloads
    the wallpaper when the file name changes."""
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    png = buffer.getvalue()
    path = WALLPAPER_DIR / f"daysleft-{today}-{hashlib.sha256(png).hexdigest()[:8]}.png"
    if not path.exists():
        WALLPAPER_DIR.mkdir(parents=True, exist_ok=True)
        partial = path.with_suffix(".partial")
        partial.write_bytes(png)
        partial.replace(path)
    return path


def preview(out: Path, today: date, size: tuple[int, int] | None) -> None:
    settings = config.load()
    image = render(year_status(today), *(size or backends.detect().screen_size()),
                   settings, dark=settings.theme != "light")
    image.save(out)
    print(f"Preview saved to {out}")


def backup() -> None:
    if BACKUP_FILE.exists():
        return  # keep the wallpaper from before Days Left was first installed
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    backends.detect().save_settings(BACKUP_FILE)
    print(f"Previous wallpaper settings saved to {BACKUP_FILE}")


def restore() -> None:
    if not BACKUP_FILE.exists():
        raise SystemExit(f"No backup found at {BACKUP_FILE}")
    backends.detect().restore_settings(BACKUP_FILE)
    print("Previous wallpaper restored")


def _size(text: str) -> tuple[int, int]:
    width, height = text.lower().split("x")
    return int(width), int(height)


def main() -> None:
    parser = argparse.ArgumentParser(prog="daysleft", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("settings", help="open the settings window")
    commands.add_parser("apply", help="render today's wallpaper and set it")
    preview_parser = commands.add_parser("preview", help="render to a file without setting it")
    preview_parser.add_argument("out", type=Path)
    preview_parser.add_argument("--date", type=date.fromisoformat, default=None,
                                help="pretend today is YYYY-MM-DD")
    preview_parser.add_argument("--size", type=_size, default=None, help="WIDTHxHEIGHT")
    commands.add_parser("backup", help="save the current wallpaper settings (first time only)")
    commands.add_parser("restore", help="bring back the wallpaper saved by backup")
    args = parser.parse_args()

    if args.command == "settings":
        from .app import run
        run()
    elif args.command == "apply":
        apply(date.today())
    elif args.command == "preview":
        preview(args.out, args.date or date.today(), args.size)
    elif args.command == "backup":
        backup()
    elif args.command == "restore":
        restore()


if __name__ == "__main__":
    main()

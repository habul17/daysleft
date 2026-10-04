"""The user's wallpaper choices, saved as JSON in ~/.config/daysleft/."""

import json
import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

CONFIG_FILE = (Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
               / "daysleft" / "settings.json")
DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "daysleft"

# The choices offered in the settings app: stored value -> label.
STYLES = {"corner": "Corner", "centered": "Centered", "dots": "Year in dots", "ring": "Progress ring"}
UNITS = {"days": "Days left", "weeks": "Weeks left", "percent": "% of year gone"}
THEMES = {"system": "Match system", "dark": "Dark", "light": "Light"}
# GNOME's accent colours; "neutral" draws progress in the text colour.
ACCENTS = {
    "neutral": None,
    "blue": (53, 132, 228),
    "teal": (33, 144, 164),
    "green": (58, 148, 74),
    "yellow": (200, 136, 0),
    "orange": (237, 91, 0),
    "red": (230, 45, 66),
    "pink": (213, 97, 153),
    "purple": (145, 65, 172),
}


@dataclass
class Settings:
    style: str = "corner"
    unit: str = "days"
    theme: str = "system"
    accent: str = "neutral"
    photo: str | None = None  # our own copy of the photo, see import_photo()


_CHOICES = {"style": STYLES, "unit": UNITS, "theme": THEMES, "accent": ACCENTS}


def load() -> Settings:
    """Saved settings, with defaults for anything missing or invalid."""
    settings = Settings()
    try:
        saved = json.loads(CONFIG_FILE.read_text())
    except (OSError, ValueError):
        return settings
    if not isinstance(saved, dict):
        return settings
    for name, choices in _CHOICES.items():
        if saved.get(name) in choices:
            setattr(settings, name, saved[name])
    if isinstance(saved.get("photo"), str):
        settings.photo = saved["photo"]
    return settings


def save(settings: Settings) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(asdict(settings), indent=2) + "\n")


def import_photo(source: Path) -> str:
    """Copies a photo into Days Left's own folder, so the wallpaper keeps
    working if the original is moved or deleted. Returns the copy's path."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    partial = DATA_DIR / ".photo-partial"
    shutil.copyfile(source, partial)
    remove_photo()
    target = DATA_DIR / f"photo{source.suffix.lower()}"
    partial.replace(target)
    return str(target)


def remove_photo() -> None:
    for old in DATA_DIR.glob("photo.*"):
        old.unlink()

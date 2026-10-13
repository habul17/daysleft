"""Draws the wallpaper in one of four styles:

  corner    big number, caption and thin progress bar in the lower-left
  centered  the same, centred on the screen
  dots      every day of the year as a dot, one row per month
  ring      a thin ring that fills up over the year, number inside

Layout is in units of one pixel on a 1080p screen. Marks are drawn at 2x on a
transparent layer, scaled down for smooth edges, then laid over the background:
a solid colour or the user's photo.
"""

import calendar
import math
import subprocess
from dataclasses import dataclass
from datetime import date
from functools import cache, lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from .settings import ACCENTS, Settings
from .year import YearStatus

SUPERSAMPLE = 2


@dataclass(frozen=True)
class Palette:
    background: tuple[int, int, int]
    ink: tuple[int, int, int]  # text colour; captions and tracks use it faded
    scrim: tuple[int, int, int]  # laid over photos so the ink stays readable
    scrim_amount: float


DARK = Palette(background=(0, 0, 0), ink=(236, 236, 238), scrim=(0, 0, 0), scrim_amount=0.5)
LIGHT = Palette(background=(242, 241, 238), ink=(28, 28, 30), scrim=(255, 255, 255), scrim_amount=0.6)


def counter(status: YearStatus, settings: Settings) -> tuple[str, str]:
    """The big number and the caption under it."""
    year = status.year
    if settings.unit == "challenge":
        return _challenge_counter(status.today, settings)
    if settings.unit == "percent":
        gone = (status.days_in_year - status.days_left) * 100 // status.days_in_year
        return f"{gone}%", f"of {year} gone"
    if settings.unit == "weeks":
        count, name, last = status.days_left // 7, "week", f"last week of {year}"
    else:
        count, name, last = status.days_left, "day", f"last day of {year}"
    if count == 0:
        return "0", last
    return str(count), f"{_plural(count, name)} left in {year}"


def _challenge_counter(today: date, settings: Settings) -> tuple[str, str]:
    """Counts up from the challenge's start date, which is day 1; before that,
    counts down to it."""
    name = settings.challenge_name.strip() or "challenge"
    start = date.fromisoformat(settings.challenge_start) if settings.challenge_start else today
    if today < start:
        until = (start - today).days
        return str(until), f"{_plural(until, 'day')} until {name}"
    day = (today - start).days + 1
    return str(day), f"{_plural(day, 'day')} in {name}"


def _plural(count: int, word: str) -> str:
    return word if count == 1 else f"{word}s"


def render(status: YearStatus, width: int, height: int, settings: Settings, dark: bool) -> Image.Image:
    palette = DARK if dark else LIGHT
    photo = _photo_or_none(settings.photo, width, height)
    canvas = _Canvas(width, height, palette, ACCENTS[settings.accent], on_photo=photo is not None)
    number, caption = counter(status, settings)
    _STYLES[settings.style](canvas, status, number, caption.upper())

    marks = canvas.layer.resize((width, height), Image.Resampling.LANCZOS)
    if photo is None:
        background = Image.new("RGBA", (width, height), (*palette.background, 255))
    else:
        scrim = Image.new("RGB", photo.size, palette.scrim)
        background = Image.blend(photo, scrim, palette.scrim_amount).convert("RGBA")
        # A soft glow in the scrim colour keeps thin marks readable over busy photos.
        glow = Image.new("RGBA", marks.size, (*palette.scrim, 0))
        blurred = marks.getchannel("A").filter(ImageFilter.GaussianBlur(height / 100))
        glow.putalpha(blurred.point(lambda alpha: min(255, alpha * 3)))
        background = Image.alpha_composite(background, glow)
    return Image.alpha_composite(background, marks).convert("RGB")


class _Canvas:
    def __init__(self, width, height, palette: Palette, accent, on_photo: bool):
        self.width, self.height = width * SUPERSAMPLE, height * SUPERSAMPLE
        self.u = self.height / 1080
        # Transparent ink-coloured pixels, so antialiased text edges keep their colour.
        self.layer = Image.new("RGBA", (self.width, self.height), (*palette.ink, 0))
        self.draw = ImageDraw.Draw(self.layer)
        self.number = (*palette.ink, 255)
        self.caption = (*palette.ink, 210 if on_photo else 128)
        self.track = (*palette.ink, 70 if on_photo else 34)
        self.fill = (*accent, 255) if accent else (*palette.ink, 210)

    def text(self, x, baseline, text, size, weight, fill, tracking=0.0, center=False):
        """Draws text with its ink starting at x (or centred on x) and returns
        the ink's left and right edges. Tracking is a fraction of the size."""
        font = _font(round(size), weight)
        advances = [font.getlength(char) + tracking * font.size for char in text]
        ink_left = font.getbbox(text[0], anchor="ls")[0]
        ink_width = sum(advances[:-1]) + font.getbbox(text[-1], anchor="ls")[2] - ink_left
        left = x - ink_width / 2 if center else x
        pen = left - ink_left
        for char, advance in zip(text, advances):
            self.draw.text((pen, baseline), char, font=font, fill=fill, anchor="ls")
            pen += advance
        return left, left + ink_width

    def caption_text(self, x, baseline, text, size, center=False):
        return self.text(x, baseline, text, size, 450, self.caption, tracking=0.32, center=center)

    def bar(self, left, right, top, progress):
        height = 3 * self.u
        box = [left, top, right, top + height]
        self.draw.rounded_rectangle(box, radius=height / 2, fill=self.track)
        box[2] = left + (right - left) * progress
        self.draw.rounded_rectangle(box, radius=height / 2, fill=self.fill)

    def ring(self, cx, cy, radius, stroke, progress):
        box = [cx - radius, cy - radius, cx + radius, cy + radius]
        self.draw.ellipse(box, outline=self.track, width=round(stroke))
        end = -90 + 360 * progress  # degrees clockwise from 3 o'clock; -90 is the top
        self.draw.arc(box, -90, end, fill=self.fill, width=round(stroke))
        middle = radius - stroke / 2
        for angle in (-90, end):  # round caps
            x = cx + middle * math.cos(math.radians(angle))
            y = cy + middle * math.sin(math.radians(angle))
            self.dot(x, y, stroke / 2, self.fill)

    def dot(self, x, y, radius, fill):
        self.draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=fill)


def _corner(c: _Canvas, status, number, caption):
    u, left = c.u, 120 * c.u
    c.text(left, 800 * u, number, 260 * u, 200, c.number)
    _, right = c.caption_text(left, 864 * u, caption, 21 * u)
    c.bar(left, right, 894 * u, status.progress)


def _centered(c: _Canvas, status, number, caption):
    u, cx = c.u, c.width / 2
    c.text(cx, 600 * u, number, 300 * u, 200, c.number, center=True)
    left, right = c.caption_text(cx, 668 * u, caption, 21 * u, center=True)
    c.bar(left, right, 698 * u, status.progress)


def _dots(c: _Canvas, status, number, caption):
    u, cx = c.u, c.width / 2
    spacing, radius = 30 * u, 5 * u
    left, top = cx - 15 * spacing, 270 * u
    today = status.days_in_year - status.days_left - 1  # 0-based day of the year

    day = 0
    for month in range(12):
        for column in range(calendar.monthrange(status.year, month + 1)[1]):
            x, y = left + column * spacing, top + month * spacing
            if day == today:
                c.draw.ellipse([x - 10 * u, y - 10 * u, x + 10 * u, y + 10 * u],
                               outline=c.fill, width=round(2 * u))
            c.dot(x, y, radius, c.fill if day <= today else c.track)
            day += 1

    c.text(cx, 760 * u, number, 120 * u, 250, c.number, center=True)
    c.caption_text(cx, 812 * u, caption, 19 * u, center=True)


def _ring(c: _Canvas, status, number, caption):
    u, cx, cy = c.u, c.width / 2, c.height / 2
    c.ring(cx, cy, 250 * u, 5 * u, status.progress)
    c.text(cx, cy + 35 * u, number, 170 * u, 200, c.number, center=True)
    c.caption_text(cx, cy + 92 * u, caption, 17 * u, center=True)


_STYLES = {"corner": _corner, "centered": _centered, "dots": _dots, "ring": _ring}


def _photo_or_none(photo: str | None, width: int, height: int) -> Image.Image | None:
    if not photo:
        return None
    try:
        return _photo(photo, Path(photo).stat().st_mtime, width, height)
    except OSError:
        return None  # photo missing or unreadable: use the plain background


@lru_cache(maxsize=2)
def _photo(path: str, mtime: float, width: int, height: int) -> Image.Image:
    """The photo cropped to fill the screen. mtime is only part of the cache key."""
    with Image.open(path) as image:
        upright = ImageOps.exif_transpose(image).convert("RGB")
    return ImageOps.fit(upright, (width, height), Image.Resampling.LANCZOS)


@cache
def _font(size: int, weight: int) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(_font_path(), size)
    try:
        axes = font.get_variation_axes()
    except OSError:
        return font  # static font: keep its built-in weight
    font.set_variation_by_axes(
        [weight if axis["name"] == b"Weight" else axis["default"] for axis in axes]
    )
    return font


@cache
def _font_path() -> str:
    return subprocess.run(
        ["fc-match", "--format=%{file}", "Ubuntu Sans"],
        capture_output=True, text=True, check=True,
    ).stdout

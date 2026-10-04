import tempfile
import unittest
from datetime import date
from pathlib import Path

from PIL import Image

from daysleft.render import DARK, LIGHT, render
from daysleft.settings import STYLES, Settings
from daysleft.year import year_status

STATUS = year_status(date(2026, 10, 4))


class RenderTest(unittest.TestCase):
    def test_every_style_and_theme(self):
        for style in STYLES:
            for dark in (True, False):
                with self.subTest(style=style, dark=dark):
                    image = render(STATUS, 960, 540, Settings(style=style), dark)
                    self.assertEqual(image.size, (960, 540))
                    background = (DARK if dark else LIGHT).background
                    self.assertEqual(image.getpixel((950, 10)), background)

    def test_other_screen_shapes(self):
        for size in [(2560, 1080), (1080, 1920)]:
            self.assertEqual(render(STATUS, *size, Settings(), True).size, size)

    def test_photo_background(self):
        with tempfile.TemporaryDirectory() as folder:
            photo = Path(folder) / "red.png"
            Image.new("RGB", (400, 300), (200, 0, 0)).save(photo)
            image = render(STATUS, 960, 540, Settings(photo=str(photo)), True)
            red, green, blue = image.getpixel((950, 10))
            self.assertGreater(red, green + 50)  # dimmed red, not the plain background

    def test_missing_photo_falls_back_to_plain(self):
        image = render(STATUS, 960, 540, Settings(photo="/nonexistent.jpg"), True)
        self.assertEqual(image.getpixel((950, 10)), DARK.background)


if __name__ == "__main__":
    unittest.main()

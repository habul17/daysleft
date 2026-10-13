import tempfile
import unittest
from pathlib import Path
from unittest import mock

from daysleft import settings as config


class SettingsTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        for name, value in [("CONFIG_FILE", self.folder / "settings.json"), ("DATA_DIR", self.folder)]:
            patcher = mock.patch.object(config, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_defaults_when_missing(self):
        self.assertEqual(config.load(), config.Settings())

    def test_round_trip(self):
        saved = config.Settings(style="ring", unit="challenge", theme="light", accent="teal",
                                photo="/x.jpg", challenge_name="100X", challenge_start="2026-10-12")
        config.save(saved)
        self.assertEqual(config.load(), saved)

    def test_invalid_values_fall_back_to_defaults(self):
        config.CONFIG_FILE.write_text(
            '{"style": "spiral", "accent": "teal", "photo": 5, "challenge_start": "yesterday"}')
        self.assertEqual(config.load(), config.Settings(accent="teal"))

    def test_corrupt_file(self):
        config.CONFIG_FILE.write_text("not json")
        self.assertEqual(config.load(), config.Settings())

    def test_import_photo_replaces_previous(self):
        first, second = self.folder / "a.JPG", self.folder / "b.png"
        first.write_bytes(b"first")
        second.write_bytes(b"second")
        config.import_photo(first)
        copy = Path(config.import_photo(second))
        self.assertEqual(copy.read_bytes(), b"second")
        self.assertEqual(sorted(p.name for p in self.folder.glob("photo.*")), ["photo.png"])


if __name__ == "__main__":
    unittest.main()

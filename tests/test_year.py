import unittest
from datetime import date

from daysleft.render import counter
from daysleft.settings import Settings
from daysleft.year import year_status


class YearStatusTest(unittest.TestCase):
    def test_mid_year(self):
        status = year_status(date(2026, 10, 4))
        self.assertEqual(status.days_left, 88)
        self.assertEqual(status.days_in_year, 365)
        self.assertAlmostEqual(status.progress, 277 / 365)

    def test_first_day(self):
        self.assertEqual(year_status(date(2026, 1, 1)).days_left, 364)

    def test_last_day(self):
        status = year_status(date(2026, 12, 31))
        self.assertEqual(status.days_left, 0)
        self.assertEqual(status.progress, 1)

    def test_leap_year(self):
        status = year_status(date(2028, 1, 1))
        self.assertEqual(status.days_in_year, 366)
        self.assertEqual(status.days_left, 365)


class CounterTest(unittest.TestCase):
    def check(self, day, unit, expected, **settings):
        self.assertEqual(counter(year_status(day), Settings(unit=unit, **settings)), expected)

    def test_days(self):
        self.check(date(2026, 10, 4), "days", ("88", "days left in 2026"))
        self.check(date(2026, 12, 30), "days", ("1", "day left in 2026"))
        self.check(date(2026, 12, 31), "days", ("0", "last day of 2026"))

    def test_weeks(self):
        self.check(date(2026, 10, 4), "weeks", ("12", "weeks left in 2026"))
        self.check(date(2026, 12, 24), "weeks", ("1", "week left in 2026"))
        self.check(date(2026, 12, 25), "weeks", ("0", "last week of 2026"))

    def test_percent(self):
        self.check(date(2026, 1, 1), "percent", ("0%", "of 2026 gone"))
        self.check(date(2026, 10, 4), "percent", ("75%", "of 2026 gone"))
        self.check(date(2026, 12, 31), "percent", ("100%", "of 2026 gone"))

    def test_challenge_counts_start_date_as_day_one(self):
        challenge = {"challenge_name": "100X", "challenge_start": "2026-10-12"}
        self.check(date(2026, 10, 12), "challenge", ("1", "day in 100X"), **challenge)
        self.check(date(2026, 10, 13), "challenge", ("2", "days in 100X"), **challenge)
        self.check(date(2027, 1, 19), "challenge", ("100", "days in 100X"), **challenge)

    def test_challenge_counts_down_before_it_starts(self):
        challenge = {"challenge_name": "100X", "challenge_start": "2026-10-12"}
        self.check(date(2026, 10, 9), "challenge", ("3", "days until 100X"), **challenge)
        self.check(date(2026, 10, 11), "challenge", ("1", "day until 100X"), **challenge)

    def test_challenge_defaults(self):
        self.check(date(2026, 10, 13), "challenge", ("1", "day in challenge"), challenge_name=" ")


if __name__ == "__main__":
    unittest.main()

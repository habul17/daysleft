"""Calendar math: how many days of the year are left on a given date."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class YearStatus:
    year: int
    days_left: int  # whole days remaining after today
    days_in_year: int  # 365, or 366 in a leap year

    @property
    def progress(self) -> float:
        """Fraction of the year used up, counting today as used."""
        return 1 - self.days_left / self.days_in_year


def year_status(today: date) -> YearStatus:
    first_day = date(today.year, 1, 1)
    last_day = date(today.year, 12, 31)
    return YearStatus(
        year=today.year,
        days_left=(last_day - today).days,
        days_in_year=(last_day - first_day).days + 1,
    )

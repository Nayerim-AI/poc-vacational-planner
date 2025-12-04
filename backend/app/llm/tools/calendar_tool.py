from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Tuple


class CalendarTool:
    """
    Mock calendar that keeps busy ranges per user and returns available ranges.
    """

    def __init__(self) -> None:
        self.busy: Dict[str, List[Tuple[date, date]]] = {}

    def seed_busy_ranges(self, user_id: str, ranges: List[Tuple[date, date]]) -> None:
        self.busy[user_id] = ranges

    def is_range_available(self, user_id: str, start: date, end: date) -> bool:
        for busy_start, busy_end in self.busy.get(user_id, []):
            if not (end < busy_start or start > busy_end):
                return False
        return True

    def get_free_date_ranges(
        self, user_id: str, start: date, end: date
    ) -> List[Tuple[date, date]]:
        current = start
        free_ranges: List[Tuple[date, date]] = []
        busy = sorted(self.busy.get(user_id, []), key=lambda r: r[0])

        for busy_start, busy_end in busy:
            if current < busy_start:
                free_ranges.append((current, busy_start - timedelta(days=1)))
            current = max(current, busy_end + timedelta(days=1))

        if current <= end:
            free_ranges.append((current, end))
        return free_ranges

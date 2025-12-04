from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple

import requests

logger = logging.getLogger(__name__)


class CalendarTool:
    """
    Mock calendar that keeps busy ranges per user and returns available ranges.
    Can ingest a public ICS URL to populate busy ranges.
    """

    def __init__(self) -> None:
        self.busy: Dict[str, List[Tuple[date, date]]] = {}

    def seed_busy_ranges(self, user_id: str, ranges: List[Tuple[date, date]]) -> None:
        self.busy[user_id] = ranges

    def add_busy_ranges(self, user_id: str, ranges: List[Tuple[date, date]]) -> None:
        existing = self.busy.get(user_id, [])
        self.busy[user_id] = existing + ranges

    def load_from_ics(self, user_id: str, url: str, timeout: int = 10) -> None:
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            ranges = self.parse_ics_content(resp.text)
            if ranges:
                self.add_busy_ranges(user_id, ranges)
                logger.info("Loaded %d busy ranges from ICS for %s", len(ranges), user_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load ICS calendar: %s", exc)

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

    @staticmethod
    def parse_ics_content(content: str) -> List[Tuple[date, date]]:
        """
        Minimal ICS parser for VEVENT busy blocks with all-day DTSTART/DTEND.
        DTEND is non-inclusive; we subtract one day.
        """
        ranges: List[Tuple[date, date]] = []
        current_start: date | None = None
        current_end: date | None = None

        def _parse_date(value: str) -> date:
            # Handles YYYYMMDD or ISO
            try:
                return datetime.strptime(value.strip(), "%Y%m%d").date()
            except ValueError:
                return date.fromisoformat(value.strip())

        for line in content.splitlines():
            if line.startswith("DTSTART"):
                _, value = line.split(":", 1)
                current_start = _parse_date(value)
            elif line.startswith("DTEND"):
                _, value = line.split(":", 1)
                current_end = _parse_date(value)
            elif line.startswith("END:VEVENT"):
                if current_start and current_end:
                    ranges.append((current_start, current_end - timedelta(days=1)))
                current_start = None
                current_end = None
        return ranges

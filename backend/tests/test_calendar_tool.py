from datetime import date

from app.llm.tools.calendar_tool import CalendarTool


def test_parse_ics_content_all_day_events():
    ics = """BEGIN:VCALENDAR
BEGIN:VEVENT
DTSTART;VALUE=DATE:20250110
DTEND;VALUE=DATE:20250112
END:VEVENT
BEGIN:VEVENT
DTSTART;VALUE=DATE:20250115
DTEND;VALUE=DATE:20250116
END:VEVENT
END:VCALENDAR"""

    ranges = CalendarTool.parse_ics_content(ics)
    assert ranges == [
        (date(2025, 1, 10), date(2025, 1, 11)),
        (date(2025, 1, 15), date(2025, 1, 15)),
    ]


def test_calendar_tool_merges_ics_with_seeded():
    tool = CalendarTool()
    tool.seed_busy_ranges("u1", [(date(2025, 2, 1), date(2025, 2, 2))])
    tool.add_busy_ranges("u1", CalendarTool.parse_ics_content("BEGIN:VEVENT\nDTSTART;VALUE=DATE:20250205\nDTEND;VALUE=DATE:20250206\nEND:VEVENT"))
    busy = tool.busy["u1"]
    assert (date(2025, 2, 1), date(2025, 2, 2)) in busy
    assert (date(2025, 2, 5), date(2025, 2, 5)) in busy

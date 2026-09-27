"""Conservative parsing. No year is guessed from today's date or publication date."""
import re
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo
from app.schemas import Schedule

SEOUL = ZoneInfo("Asia/Seoul")
FULL_DATE = re.compile(
    r"(?<!\d)(20\d{2})\s*(?:[./-]|년)\s*(\d{1,2})\s*(?:[./-]|월)\s*(\d{1,2})(?:\s*일)?(?!\d)"
)
CLOCK = re.compile(r"(?<!\d)([01]?\d|2[0-3])\s*(?::\s*([0-5]\d)|시(?:\s*([0-5]?\d)분)?)(?!\d)")

def local_today(now: int | None = None) -> date:
    return datetime.fromtimestamp(now, tz=SEOUL).date() if now is not None else datetime.now(SEOUL).date()

def dates_in_text(text: str) -> list[tuple[date, time | None]]:
    found = []
    matches = list(FULL_DATE.finditer(text))
    for index, match in enumerate(matches):
        try:
            d = date(*map(int, match.groups()))
        except ValueError:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        # Ignore an abbreviated range's end-time, which must not become a start-time.
        tail = text[match.end():end]
        clock = CLOCK.search(tail[:30]) if not re.search(r"[~∼～]", tail) else None
        t = None
        if clock:
            t = time(int(clock[1]), int(clock[2] or clock[3] or 0))
        found.append((d, t))
    return found

def deadline_values(schedules: list[Schedule]) -> tuple[date | None, int | None]:
    applications = [s for s in schedules if s.kind == "application"]
    if not applications or any(s.end_date is None for s in applications):
        return None, None
    # Multiple explicitly stated application windows: remains open until the last close.
    values = [(s.end_date, int(datetime.combine(s.end_date, s.end_time or time(23,59,59),
                                                tzinfo=SEOUL).timestamp()))
              for s in applications]
    return max(values, key=lambda x: x[1])

def deadline_badge(deadline_date, deadline_at, now: int):
    if deadline_date is None or deadline_at is None:
        return None, "마감 미정 · 원문 확인", False
    closed = deadline_at < now
    day = (deadline_date - local_today(now)).days
    return day, "마감" if closed else ("D-Day" if day == 0 else f"D-{day}"), closed

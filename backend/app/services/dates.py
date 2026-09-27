"""Conservative parsing. No year is guessed from today's date or publication date."""
import re
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo
from app.schemas import Schedule

SEOUL = ZoneInfo("Asia/Seoul")
FULL_DATE = re.compile(
    r"(?<!\d)(20\d{2}|['’]\d{2})\s*(?:[./-]|년)\s*(\d{1,2})\s*(?:[./-]|월)\s*(\d{1,2})(?:\s*일)?(?!\d)"
)
SHORT_DATE = re.compile(r"(?<![\d.])(\d{1,2})\s*(?:[./-]|월)\s*(\d{1,2})(?:\s*일)?(?!\d)")
YEAR_MONTH = re.compile(r"(?<!\d)20\d{2}\s*(?:[./-]|년)\s*\d{1,2}\s*(?:월|[./-])")
CLOCK = re.compile(r"(?<!\d)([01]?\d|2[0-3])\s*(?::\s*([0-5]\d)|시(?:\s*([0-5]?\d)분)?)(?!\d)")

def has_date_expression(text: str) -> bool:
    return bool(FULL_DATE.search(text) or SHORT_DATE.search(text) or YEAR_MONTH.search(text))

def local_today(now: int | None = None) -> date:
    return datetime.fromtimestamp(now, tz=SEOUL).date() if now is not None else datetime.now(SEOUL).date()

def dates_in_text(text: str) -> list[tuple[date, time | None]]:
    found = []
    matches = []
    full_matches = list(FULL_DATE.finditer(text))
    for match in full_matches:
        try:
            year, month, day = match.groups()
            d = date(2000 + int(year[1:]) if year.startswith(("'", "’")) else int(year),
                     int(month), int(day))
        except ValueError:
            continue
        matches.append((match.start(), match.end(), d))
    for match in SHORT_DATE.finditer(text):
        if any(start <= match.start() < end for start, end, _ in matches):
            continue
        previous = max(((start, end, d) for start, end, d in matches
                        if end <= match.start()), key=lambda item: item[1], default=None)
        if previous is None or not re.fullmatch(
            r"\s*\.?\s*(?:\([^)]*\)\s*)?[~∼～]\s*", text[previous[1]:match.start()]):
            continue
        try:
            d = date(previous[2].year, int(match[1]), int(match[2]))
        except ValueError:
            continue
        if d < previous[2]:
            continue
        matches.append((match.start(), match.end(), d))
    matches.sort(key=lambda item: item[0])
    for index, (_start, end_pos, d) in enumerate(matches):
        end = matches[index + 1][0] if index + 1 < len(matches) else len(text)
        # Ignore an abbreviated range's end-time, which must not become a start-time.
        tail = text[end_pos:end]
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

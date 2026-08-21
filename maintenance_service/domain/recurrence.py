from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .amendments import parse_local


WEEKDAY_NUMBER = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


def expand_weekly(state, search_start, search_end):
    rule = state["rule"]
    zone = ZoneInfo(state["timezone"])
    local_start = parse_local(rule["start"])
    until = parse_local(rule["until"]) if "until" in rule else None
    count = rule.get("count")
    weekdays = {WEEKDAY_NUMBER[value] for value in rule["weekdays"]}
    interval = rule["interval"]
    cursor = local_start.date()
    emitted = 0
    results = []
    local_limit = search_end.astimezone(zone).date() + timedelta(days=8)
    while cursor <= local_limit:
        candidate = datetime.combine(cursor, local_start.time())
        week = (cursor - local_start.date()).days // 7
        eligible = cursor.weekday() in weekdays and week >= 0 and week % interval == 0
        if eligible and candidate >= local_start and (until is None or candidate <= until):
            emitted += 1
            if count is not None and emitted > count:
                break
            start = candidate.replace(tzinfo=zone).astimezone(timezone.utc)
            end = (candidate + timedelta(minutes=rule["duration_minutes"])).replace(
                tzinfo=zone
            ).astimezone(timezone.utc)
            if start < search_end and end > search_start:
                results.append((start, end))
        if until is not None and candidate > until:
            break
        cursor += timedelta(days=1)
    return results

from datetime import datetime, timedelta, timezone
from calendar import monthrange
from maintenance_service.domain.errors import InvalidSchedule


def utc(value):
    if value.tzinfo is None:
        raise InvalidSchedule("timestamp requires timezone")
    return value.astimezone(timezone.utc)


def add_months(value, months):
    target = (value.year * 12 + (value.month - 1)) + months
    year, target_month = divmod(target, 12)
    month = target_month + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def start_of_week(value):
    return value - timedelta(
        days=value.weekday(),
        hours=value.hour,
        minutes=value.minute,
        seconds=value.second,
        microseconds=value.microsecond,
    )


def end_of_week(value):
    return start_of_week(value) + timedelta(days=7)


def weekday_occurrences(start, end, weekday):
    if not 0 <= weekday <= 6:
        raise InvalidSchedule("weekday is invalid")
    cursor = start + timedelta(days=(weekday - start.weekday()) % 7)
    output = []
    while cursor < end:
        output.append(cursor)
        cursor += timedelta(days=7)
    return tuple(output)


def midpoint(start, end):
    if end <= start:
        raise InvalidSchedule("interval must be positive")
    return start + (end - start) / 2


def intersects(start, end, other_start, other_end):
    return start < other_end and other_start < end


def adjacent(start, end, other_start, other_end):
    return end == other_start or other_end == start


def duration_minutes(start, end):
    return int((end - start).total_seconds() // 60)


def clamp(value, lower, upper):
    return max(lower, min(value, upper))


def days_between(start, end):
    return (end - start).days

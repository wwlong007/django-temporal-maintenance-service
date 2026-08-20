from dataclasses import dataclass
from datetime import datetime, timedelta
from .errors import InvalidSchedule

MAX_RANGE = timedelta(days=366)
DEFAULT_LIMIT = 100
MAX_LIMIT = 500


@dataclass(frozen=True)
class AvailabilityRange:
    start: datetime
    end: datetime

    def __post_init__(self):
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise InvalidSchedule("availability timestamps require offsets")
        if self.end <= self.start:
            raise InvalidSchedule("availability range must be positive")
        if self.end - self.start > MAX_RANGE:
            raise InvalidSchedule("availability range exceeds one year")

    def intersect(self, start, end):
        lower, upper = max(self.start, start), min(self.end, end)
        return None if lower >= upper else AvailabilityRange(lower, upper)

    def contains(self, instant):
        return self.start <= instant < self.end

    @property
    def duration(self):
        return self.end - self.start


@dataclass(frozen=True)
class PageRequest:
    limit: int = DEFAULT_LIMIT
    cursor: str | None = None

    def __post_init__(self):
        if not DEFAULT_LIMIT - 99 <= self.limit <= MAX_LIMIT:
            raise InvalidSchedule("page limit is outside the supported range")


def validate_limit(value):
    if value is None:
        return DEFAULT_LIMIT
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise InvalidSchedule("limit must be an integer") from exc
    if parsed < 1 or parsed > MAX_LIMIT:
        raise InvalidSchedule("page limit is outside the supported range")
    return parsed


def ensure_sorted(intervals):
    previous = None
    for interval in intervals:
        if previous is not None and interval.start < previous:
            raise InvalidSchedule("availability intervals are unsorted")
        previous = interval.end
    return tuple(intervals)


def count_covered(intervals):
    total = timedelta()
    for interval in intervals:
        total += interval.end - interval.start
    return total


def coverage_ratio(intervals, requested):
    if not requested.duration:
        return 0.0
    return count_covered(intervals).total_seconds() / requested.duration.total_seconds()


def clip_rows(rows, requested):
    result = []
    for row in rows:
        lower, upper = max(row[0], requested.start), min(row[1], requested.end)
        if lower < upper:
            result.append((lower, upper, *row[2:]))
    return tuple(result)


def is_adjacent(left, right):
    return left.end == right.start


def window_label(start, end):
    return f"{start.isoformat()}/{end.isoformat()}"

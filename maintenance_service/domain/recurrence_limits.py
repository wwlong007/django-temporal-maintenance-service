from dataclasses import dataclass
from datetime import datetime, timedelta
from .errors import InvalidSchedule


@dataclass(frozen=True)
class ExpansionWindow:
    start: datetime
    end: datetime
    maximum_occurrences: int

    def __post_init__(self):
        if self.end <= self.start:
            raise InvalidSchedule("expansion window must be positive")
        if self.maximum_occurrences < 1:
            raise InvalidSchedule("maximum occurrences must be positive")

    @property
    def duration(self):
        return self.end - self.start

    def contains(self, value):
        return self.start <= value < self.end

    def clip(self, start, end):
        lower, upper = max(start, self.start), min(end, self.end)
        return None if upper <= lower else (lower, upper)


DEFAULT_MAX_OCCURRENCES = 10_000
MAX_EXPANSION_DAYS = 731


def validate_expansion_range(start, end, maximum_occurrences=DEFAULT_MAX_OCCURRENCES):
    window = ExpansionWindow(start, end, maximum_occurrences)
    if window.duration > timedelta(days=MAX_EXPANSION_DAYS):
        raise InvalidSchedule("expansion range exceeds supported horizon")
    return window


def enforce_limit(values, window):
    result = []
    for value in values:
        if len(result) >= window.maximum_occurrences:
            raise InvalidSchedule("recurrence expansion exceeds occurrence limit")
        result.append(value)
    return tuple(result)


def estimate_weekly_count(start, end, interval, weekdays):
    weeks = max(1, ((end - start).days // 7) + 1)
    return ((weeks + interval - 1) // interval) * max(1, len(weekdays))


def estimate_monthly_count(start, end, interval):
    months = max(1, ((end.year - start.year) * 12) + end.month - start.month + 1)
    return (months + interval - 1) // interval


def estimate_rule_count(rule, start, end):
    if rule.get("frequency") == "weekly":
        estimated = estimate_weekly_count(
            start, end, int(rule.get("interval", 1)), rule.get("weekdays", [])
        )
    else:
        estimated = estimate_monthly_count(start, end, int(rule.get("interval", 1)))
    if rule.get("count") is not None:
        estimated = min(estimated, int(rule["count"]))
    return estimated


def preflight(rule, start, end, limit=DEFAULT_MAX_OCCURRENCES):
    window = validate_expansion_range(start, end, limit)
    if estimate_rule_count(rule, start, end) > limit:
        raise InvalidSchedule("recurrence rule is too dense for the requested range")
    return window

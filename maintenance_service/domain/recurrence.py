from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .rules import parse_local_datetime, parse_timezone
from .types import Occurrence


WEEKDAY_NUMBER = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


@dataclass(frozen=True)
class WeeklyRule:
    start: datetime
    weekdays: frozenset[int]
    interval: int
    duration: timedelta
    count: int | None
    until: datetime | None

    @classmethod
    def from_state(cls, state):
        rule = state["rule"]
        return cls(
            start=parse_local_datetime(rule["start"]),
            weekdays=frozenset(WEEKDAY_NUMBER[item] for item in rule["weekdays"]),
            interval=rule["interval"],
            duration=timedelta(minutes=rule["duration_minutes"]),
            count=rule.get("count"),
            until=parse_local_datetime(rule["until"]) if "until" in rule else None,
        )

    def includes_date(self, value):
        if value < self.start.date() or value.weekday() not in self.weekdays:
            return False
        week_index = (value - self.start.date()).days // 7
        return week_index % self.interval == 0

    def local_candidate(self, value):
        return datetime.combine(value, self.start.time())


def local_candidates(rule, final_date):
    cursor = rule.start.date()
    while cursor <= final_date:
        if rule.includes_date(cursor):
            candidate = rule.local_candidate(cursor)
            if candidate >= rule.start:
                if rule.until is not None and candidate > rule.until:
                    return
                yield candidate
        cursor += timedelta(days=1)


def search_limit(search_end, zone):
    return search_end.astimezone(zone).date() + timedelta(days=8)


def bind_occurrence(candidate, duration, zone):
    start = candidate.replace(tzinfo=zone).astimezone(timezone.utc)
    end = (candidate + duration).replace(tzinfo=zone).astimezone(timezone.utc)
    return start, end


def expand_weekly(state, search_start, search_end, window_id=""):
    rule = WeeklyRule.from_state(state)
    zone = parse_timezone(state["timezone"])
    emitted = 0
    values = []
    for candidate in local_candidates(rule, search_limit(search_end, zone)):
        emitted += 1
        if rule.count is not None and emitted > rule.count:
            break
        start, end = bind_occurrence(candidate, rule.duration, zone)
        if start < search_end and end > search_start:
            values.append(
                Occurrence(
                    start=start,
                    end=end,
                    priority=state["priority"],
                    window_id=window_id,
                )
            )
    return values


def expand_slices(window_id, slices, search_start, search_end):
    values = []
    for index, item in enumerate(slices):
        if not item.state["active"]:
            continue
        following = slices[index + 1].effective_from if index + 1 < len(slices) else None
        for occurrence in expand_weekly(
            item.state, max(search_start, item.effective_from), search_end, window_id
        ):
            if occurrence.start < item.effective_from:
                continue
            if following is not None and occurrence.start >= following:
                continue
            values.append(occurrence)
    return values

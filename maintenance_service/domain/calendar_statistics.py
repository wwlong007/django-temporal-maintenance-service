from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable
from .calendar_composition import compose


@dataclass(frozen=True)
class CalendarStatistics:
    source_count: int
    raw_occurrence_count: int
    effective_interval_count: int
    maintenance_seconds: float
    available_seconds: float
    conflict_count: int

    def as_dict(self):
        return self.__dict__


def seconds(intervals):
    return sum((item.end - item.start).total_seconds() for item in intervals)


def statistics(rows, start, end, conflicts=()):
    composition = compose(rows)
    maintenance = tuple(composition.maintenance_for(start, end))
    available = tuple(composition.available_for(start, end))
    return CalendarStatistics(
        len({row[3] for row in rows}),
        len(rows),
        len(maintenance),
        seconds([item.interval for item in maintenance]),
        seconds(available),
        len(tuple(conflicts)),
    )


def availability_percent(stats):
    total = stats.available_seconds + stats.maintenance_seconds
    return 100.0 if not total else round((stats.available_seconds / total) * 100, 4)


def maintenance_percent(stats):
    return round(100.0 - availability_percent(stats), 4)


def source_distribution(rows):
    output = {}
    for start, end, priority, source, revision in rows:
        output.setdefault(
            source,
            {
                "occurrences": 0,
                "seconds": 0.0,
                "priority": priority,
                "revision": revision,
            },
        )
        output[source]["occurrences"] += 1
        output[source]["seconds"] += (end - start).total_seconds()
    return dict(sorted(output.items()))


def priority_distribution(rows):
    output = {}
    for start, end, priority, *_ in rows:
        output[priority] = output.get(priority, 0) + 1
    return dict(sorted(output.items()))


def longest_interval(rows):
    return max(rows, key=lambda item: (item[1] - item[0], item[3])) if rows else None


def shortest_interval(rows):
    return min(rows, key=lambda item: (item[1] - item[0], item[3])) if rows else None


def average_duration_seconds(rows):
    return (
        0.0
        if not rows
        else sum((row[1] - row[0]).total_seconds() for row in rows) / len(rows)
    )


def summarize(rows, start, end, conflicts=()):
    stats = statistics(rows, start, end, conflicts)
    return {
        **stats.as_dict(),
        "availability_percent": availability_percent(stats),
        "maintenance_percent": maintenance_percent(stats),
        "sources": source_distribution(rows),
        "priorities": priority_distribution(rows),
        "average_duration_seconds": average_duration_seconds(rows),
    }

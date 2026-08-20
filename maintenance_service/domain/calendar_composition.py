from dataclasses import dataclass
from datetime import datetime
from typing import Iterable
from .interval_algebra import Interval
from .interval_set import IntervalSet, SourcedInterval
from .errors import InvalidSchedule


@dataclass(frozen=True)
class CalendarOccurrence:
    window_id: str
    start: datetime
    end: datetime
    priority: int
    revision: int

    def interval(self):
        return Interval(self.start, self.end)

    def sourced(self):
        return SourcedInterval(
            self.interval(), self.priority, self.window_id, self.revision
        )


@dataclass(frozen=True)
class CompositionResult:
    effective: IntervalSet
    source_count: int

    def maintenance_for(self, start, end):
        return self.effective.bounded(start, end)

    def available_for(self, start, end):
        return self.maintenance_for(start, end).complement(start, end)


def build_occurrences(rows):
    output = []
    for row in rows:
        if isinstance(row, CalendarOccurrence):
            output.append(row)
            continue
        start, end, priority, source, revision = row
        output.append(CalendarOccurrence(source, start, end, priority, revision))
    return tuple(output)


def compose(rows: Iterable):
    occurrences = build_occurrences(rows)
    return CompositionResult(
        IntervalSet(item.sourced() for item in occurrences).resolve_priority(),
        len(occurrences),
    )


def merge_adjacent_by_source(values):
    output = []
    for value in sorted(
        values, key=lambda item: (item.start, item.end, item.window_id)
    ):
        if (
            output
            and output[-1].window_id == value.window_id
            and output[-1].priority == value.priority
            and output[-1].revision == value.revision
            and output[-1].end == value.start
        ):
            previous = output[-1]
            output[-1] = CalendarOccurrence(
                previous.window_id,
                previous.start,
                value.end,
                previous.priority,
                previous.revision,
            )
        else:
            output.append(value)
    return tuple(output)


def validate_occurrences(values):
    for value in values:
        if value.end <= value.start:
            raise InvalidSchedule("calendar occurrence must have a positive interval")
        if not value.window_id:
            raise InvalidSchedule("calendar occurrence must have a source")
    return tuple(values)


def resolve_at(rows, instant):
    values = [
        value for value in build_occurrences(rows) if value.start <= instant < value.end
    ]
    return (
        max(values, key=lambda item: (item.priority, item.revision, item.window_id))
        if values
        else None
    )


def sources(rows):
    return tuple(sorted({value.window_id for value in build_occurrences(rows)}))


def count_by_source(rows):
    output = {}
    for value in build_occurrences(rows):
        output[value.window_id] = output.get(value.window_id, 0) + 1
    return output


def source_intervals(rows, window_id):
    return tuple(
        value for value in build_occurrences(rows) if value.window_id == window_id
    )


def has_source(rows, window_id):
    return any(value.window_id == window_id for value in build_occurrences(rows))


def clip(rows, start, end):
    output = []
    for value in build_occurrences(rows):
        lower, upper = max(start, value.start), min(end, value.end)
        if lower < upper:
            output.append(
                CalendarOccurrence(
                    value.window_id, lower, upper, value.priority, value.revision
                )
            )
    return tuple(output)


def to_rows(result):
    return tuple(
        (
            value.interval.start,
            value.interval.end,
            value.priority,
            value.source,
            value.revision,
        )
        for value in result.effective
    )

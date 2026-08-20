from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Iterator
from .interval_algebra import Interval


@dataclass(frozen=True)
class SourcedInterval:
    interval: Interval
    priority: int
    source: str
    revision: int = 0


class IntervalSet:
    def __init__(self, values: Iterable[SourcedInterval] = ()):
        self._values = tuple(
            sorted(
                values,
                key=lambda value: (
                    value.interval.start,
                    value.interval.end,
                    -value.priority,
                    value.source,
                ),
            )
        )

    def __iter__(self) -> Iterator[SourcedInterval]:
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def append(self, value: SourcedInterval):
        return IntervalSet((*self._values, value))

    def bounded(self, start: datetime, end: datetime):
        result = []
        for value in self._values:
            if value.interval.end <= start or value.interval.start >= end:
                continue
            result.append(
                SourcedInterval(
                    Interval(
                        max(start, value.interval.start), min(end, value.interval.end)
                    ),
                    value.priority,
                    value.source,
                    value.revision,
                )
            )
        return IntervalSet(result)

    def coalesce(self):
        if not self._values:
            return self
        output = [self._values[0]]
        for value in self._values[1:]:
            previous = output[-1]
            compatible = (
                previous.priority == value.priority
                and previous.source == value.source
                and previous.revision == value.revision
            )
            if compatible and value.interval.start <= previous.interval.end:
                output[-1] = SourcedInterval(
                    Interval(
                        previous.interval.start,
                        max(previous.interval.end, value.interval.end),
                    ),
                    value.priority,
                    value.source,
                    value.revision,
                )
            else:
                output.append(value)
        return IntervalSet(output)

    def resolve_priority(self):
        boundaries = sorted(
            {
                point
                for value in self._values
                for point in (value.interval.start, value.interval.end)
            }
        )
        result = []
        for start, end in zip(boundaries, boundaries[1:]):
            candidates = [
                value
                for value in self._values
                if value.interval.start < end and start < value.interval.end
            ]
            if not candidates:
                continue
            winner = max(
                candidates,
                key=lambda value: (value.priority, value.revision, value.source),
            )
            result.append(
                SourcedInterval(
                    Interval(start, end),
                    winner.priority,
                    winner.source,
                    winner.revision,
                )
            )
        return IntervalSet(result).coalesce()

    def complement(self, start: datetime, end: datetime):
        occupied = self.bounded(start, end).resolve_priority()
        cursor = start
        output = []
        for value in occupied:
            if cursor < value.interval.start:
                output.append(Interval(cursor, value.interval.start))
            cursor = max(cursor, value.interval.end)
        if cursor < end:
            output.append(Interval(cursor, end))
        return tuple(output)

    def serialize(self):
        return [
            {
                "start": value.interval.start,
                "end": value.interval.end,
                "priority": value.priority,
                "source_window_id": value.source,
                "revision": value.revision,
            }
            for value in self._values
        ]

from dataclasses import dataclass
from typing import Iterable
from .interval_algebra import Interval
from .interval_set import IntervalSet, SourcedInterval


@dataclass(frozen=True)
class Conflict:
    start: object
    end: object
    winner: str
    loser: str
    winner_priority: int
    loser_priority: int

    def as_dict(self):
        return {
            "start": self.start,
            "end": self.end,
            "winner": self.winner,
            "loser": self.loser,
            "winner_priority": self.winner_priority,
            "loser_priority": self.loser_priority,
        }


def as_sourced(rows: Iterable[tuple]):
    return tuple(
        SourcedInterval(Interval(start, end), priority, source, revision)
        for start, end, priority, source, revision in rows
    )


def precedence_key(item):
    return (item.priority, item.revision, item.source)


def diagnose(rows: Iterable[tuple]):
    values = as_sourced(rows)
    result = []
    for index, left in enumerate(values):
        for right in values[index + 1 :]:
            if not left.interval.overlaps(right.interval):
                continue
            winner, loser = (
                (left, right)
                if precedence_key(left) >= precedence_key(right)
                else (right, left)
            )
            overlap = Interval(
                max(left.interval.start, right.interval.start),
                min(left.interval.end, right.interval.end),
            )
            result.append(
                Conflict(
                    overlap.start,
                    overlap.end,
                    winner.source,
                    loser.source,
                    winner.priority,
                    loser.priority,
                )
            )
    return tuple(
        sorted(result, key=lambda item: (item.start, item.end, item.winner, item.loser))
    )


def effective(rows: Iterable[tuple]):
    return IntervalSet(as_sourced(rows)).resolve_priority()


def no_overlapping_effective_intervals(rows: Iterable[tuple]):
    values = tuple(effective(rows))
    return all(
        not left.interval.overlaps(right.interval)
        for left, right in zip(values, values[1:])
    )


def ownership_at(rows: Iterable[tuple], instant):
    candidates = [item for item in as_sourced(rows) if item.interval.contains(instant)]
    return max(candidates, key=precedence_key) if candidates else None


def explain(rows: Iterable[tuple], instant):
    winner = ownership_at(rows, instant)
    if winner is None:
        return {"maintenance": False, "source_window_id": None, "priority": None}
    return {
        "maintenance": True,
        "source_window_id": winner.source,
        "priority": winner.priority,
    }

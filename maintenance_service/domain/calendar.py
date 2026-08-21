from dataclasses import dataclass

from .intervals import partition
from .recurrence import expand_slices
from .timeline import resolved_snapshots


@dataclass(frozen=True)
class CalendarWindow:
    window_id: str
    records: tuple

    def slices(self):
        return resolved_snapshots(self.records)

    def occurrences(self, start, end):
        return expand_slices(self.window_id, self.slices(), start, end)


def window_from_history(history):
    return CalendarWindow(history.window.window_id, history.records)


def collect_occurrences(histories, start, end):
    values = []
    for history in histories:
        calendar_window = window_from_history(history)
        values.extend(calendar_window.occurrences(start, end))
    return values


def compose_availability(histories, start, end):
    occurrences = collect_occurrences(histories, start, end)
    return partition(start, end, occurrences)


def interval_is_partition(intervals, start, end):
    if not intervals:
        return False
    if intervals[0]["start"] != start or intervals[-1]["end"] != end:
        return False
    return all(
        left["end"] == right["start"]
        for left, right in zip(intervals, intervals[1:])
    )


def maintenance_sources(intervals):
    return {
        item["source_window_id"]
        for item in intervals
        if item.get("maintenance") and "source_window_id" in item
    }


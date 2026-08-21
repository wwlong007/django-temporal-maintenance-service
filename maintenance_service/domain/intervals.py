from collections import defaultdict

from .types import AvailabilitySegment, Occurrence


def clip_occurrences(start, end, occurrences):
    values = []
    for occurrence in occurrences:
        if not isinstance(occurrence, Occurrence):
            occurrence = Occurrence(*occurrence)
        clipped = occurrence.clipped(start, end)
        if clipped is not None:
            values.append(clipped)
    return values


def boundary_index(start, end, occurrences):
    events = defaultdict(list)
    events[start]
    events[end]
    for item in occurrences:
        events[item.start].append((True, item))
        events[item.end].append((False, item))
    return events


def winner(active):
    if not active:
        return None
    return max(active, key=lambda item: (item.priority, item.window_id))


def build_segments(start, end, occurrences):
    clipped = clip_occurrences(start, end, occurrences)
    events = boundary_index(start, end, clipped)
    points = sorted(events)
    active = set()
    result = []
    for index, left in enumerate(points[:-1]):
        for entering, item in events[left]:
            if entering:
                active.add(item)
            else:
                active.discard(item)
        right = points[index + 1]
        selected = winner(active)
        segment = AvailabilitySegment(
            start=left,
            end=right,
            source_window_id=selected.window_id if selected else None,
        )
        append_segment(result, segment)
    return result


def append_segment(segments, segment):
    if segment.start >= segment.end:
        return
    if (
        segments
        and segments[-1].end == segment.start
        and segments[-1].source_window_id == segment.source_window_id
    ):
        previous = segments[-1]
        segments[-1] = AvailabilitySegment(
            previous.start, segment.end, previous.source_window_id
        )
    else:
        segments.append(segment)


def partition(start, end, occurrences):
    return [item.as_dict() for item in build_segments(start, end, occurrences)]

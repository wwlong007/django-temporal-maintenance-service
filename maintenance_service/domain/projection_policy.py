from dataclasses import dataclass
from datetime import datetime
from .errors import InvalidSchedule


@dataclass(frozen=True)
class ProjectionBoundary:
    start: datetime
    end: datetime
    revision: int

    def __post_init__(self):
        if self.end <= self.start:
            raise InvalidSchedule("projection boundary must be positive")
        if self.revision < 0:
            raise InvalidSchedule("projection revision is invalid")


def accepts_occurrence(boundary, start, end, revision):
    return (
        revision == boundary.revision
        and boundary.start <= start
        and end <= boundary.end
    )


def stale(revision, current_revision):
    return revision != current_revision


def range_key(start, end):
    return (start.isoformat(), end.isoformat())


def projection_key(window_id, start):
    return f"{window_id}:{start.isoformat()}"


def requires_refresh(old_rule, new_rule, old_timezone, new_timezone):
    return old_rule != new_rule or old_timezone != new_timezone


def revision_after_write(revision):
    if revision < 0:
        raise InvalidSchedule("projection revision is invalid")
    return revision + 1


def same_boundary(left, right):
    return (
        left.start == right.start
        and left.end == right.end
        and left.revision == right.revision
    )


def describe(boundary):
    return f"revision={boundary.revision} {boundary.start.isoformat()}..{boundary.end.isoformat()}"

from dataclasses import dataclass
from datetime import datetime, timezone
from .errors import VersionConflict, InvalidSchedule


@dataclass(frozen=True)
class VersionToken:
    value: int
    issued_at: datetime

    def __post_init__(self):
        if self.value < 0:
            raise InvalidSchedule("revision cannot be negative")

    def next(self):
        return VersionToken(self.value + 1, datetime.now(timezone.utc))

    def matches(self, value):
        try:
            return self.value == int(value)
        except (TypeError, ValueError):
            return False


@dataclass(frozen=True)
class RevisionSnapshot:
    calendar_revision: int
    window_version: int
    observed_at: datetime

    def is_current_for(self, calendar_revision, window_version):
        return (
            self.calendar_revision == calendar_revision
            and self.window_version == window_version
        )


def require_version(expected, actual):
    try:
        expected_value = int(expected)
    except (TypeError, ValueError) as exc:
        raise VersionConflict("version conflict") from exc
    if expected_value != actual:
        raise VersionConflict("version conflict")
    return VersionToken(actual, datetime.now(timezone.utc))


def advance_calendar_revision(revision):
    if revision >= 2_147_483_647:
        raise InvalidSchedule("calendar revision exhausted")
    return revision + 1


def stable_snapshot(calendar_revision, window_version):
    return RevisionSnapshot(
        calendar_revision, window_version, datetime.now(timezone.utc)
    )

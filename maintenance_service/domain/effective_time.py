from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from django.utils.dateparse import parse_datetime

from maintenance_service.domain.errors import InvalidSchedule


def parse_instant(value, name="effective_from"):
    parsed = value if isinstance(value, datetime) else parse_datetime(str(value or ""))
    if parsed is None or parsed.tzinfo is None:
        raise InvalidSchedule(f"{name} must be an ISO-8601 instant with an offset")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class EffectiveGeneration:
    effective_from: datetime
    effective_to: datetime | None
    calendar: str
    timezone: str
    rule: dict
    exceptions: dict
    priority: int
    active: bool
    window_version: int
    committed_revision: int

    def contains(self, instant):
        return self.effective_from <= instant and (
            self.effective_to is None or instant < self.effective_to
        )


def visible_generations(rows: Iterable, revision: int):
    visible = sorted(
        (row for row in rows if row.committed_revision <= revision),
        key=lambda row: (row.effective_from, row.committed_revision, row.window_version),
    )
    return tuple(
        EffectiveGeneration(
            row.effective_from,
            visible[index + 1].effective_from if index + 1 < len(visible) else None,
            row.calendar,
            row.timezone,
            row.rule,
            row.exceptions,
            row.priority,
            row.active,
            row.window_version,
            row.committed_revision,
        )
        for index, row in enumerate(visible)
    )


def generation_at(generations, instant):
    matches = [item for item in generations if item.contains(instant)]
    return matches[-1] if matches else None

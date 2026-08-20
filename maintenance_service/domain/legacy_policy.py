from dataclasses import dataclass
from typing import Iterable
from .errors import InvalidSchedule
from .rule_validation import validate_timezone
from .timezone_policy import resolve_local


@dataclass(frozen=True)
class LegacyScheduleValue:
    organization: str
    resource: str
    window_id: str
    timezone: str
    local_start: str
    weekday: str
    duration_minutes: int
    priority: int

    def key(self):
        return (
            self.organization,
            self.resource,
            self.window_id,
            self.timezone,
            self.local_start,
            self.weekday,
            self.duration_minutes,
            self.priority,
        )

    def window_payload(self):
        return {
            "window_id": self.window_id,
            "calendar": "legacy",
            "timezone": self.timezone,
            "priority": self.priority,
            "exceptions": {},
            "rule": {
                "frequency": "weekly",
                "start": self.local_start,
                "weekdays": [self.weekday],
                "duration_minutes": self.duration_minutes,
                "count": 1,
            },
        }


def coerce_record(record):
    if not isinstance(record, dict):
        raise InvalidSchedule("legacy schedule must be an object")
    fields = ("organization", "resource", "window_id", "timezone", "local_start")
    if any(not record.get(field) for field in fields):
        raise InvalidSchedule("legacy schedule has required fields missing")
    timezone_name = validate_timezone(record["timezone"])
    resolve_local(record["local_start"], timezone_name)
    weekday = str(record.get("weekday", "MO")).upper()
    if weekday not in {"MO", "TU", "WE", "TH", "FR", "SA", "SU"}:
        raise InvalidSchedule("legacy weekday is invalid")
    try:
        duration, priority = int(record.get("duration_minutes", 60)), int(
            record.get("priority", 0)
        )
    except (TypeError, ValueError) as exc:
        raise InvalidSchedule("legacy numeric value is invalid") from exc
    if duration <= 0:
        raise InvalidSchedule("legacy duration must be positive")
    return LegacyScheduleValue(
        str(record["organization"]),
        str(record["resource"]),
        str(record["window_id"]),
        timezone_name,
        str(record["local_start"]),
        weekday,
        duration,
        priority,
    )


def normalize_records(records: Iterable[dict]):
    output = []
    seen = set()
    for record in records:
        value = coerce_record(record)
        if value.key() in seen:
            continue
        seen.add(value.key())
        output.append(value)
    return tuple(sorted(output, key=lambda item: item.key()))

from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict
from maintenance_service.domain.errors import InvalidSchedule
from maintenance_service.domain.rule_validation import validate_timezone
from maintenance_service.domain.timezone_policy import resolve_local


@dataclass(frozen=True)
class LegacyRecord:
    organization: str
    resource: str
    window_id: str
    timezone: str
    local_start: str
    weekday: str
    duration_minutes: int
    priority: int = 0


@dataclass(frozen=True)
class UpgradePlan:
    records: tuple[LegacyRecord, ...]
    duplicates_removed: int

    def grouped(self):
        result = defaultdict(list)
        for record in self.records:
            result[(record.organization, record.resource)].append(record)
        return dict(result)


def parse_legacy_record(payload):
    required = ("organization", "resource", "window_id", "timezone", "local_start")
    missing = [field for field in required if not payload.get(field)]
    if missing:
        raise InvalidSchedule("legacy record missing: " + ", ".join(missing))
    timezone_name = validate_timezone(payload["timezone"])
    resolve_local(payload["local_start"], timezone_name)
    weekday = str(payload.get("weekday", "MO")).upper()
    if weekday not in {"MO", "TU", "WE", "TH", "FR", "SA", "SU"}:
        raise InvalidSchedule("legacy weekday is invalid")
    try:
        duration = int(payload.get("duration_minutes", 60))
        priority = int(payload.get("priority", 0))
    except (TypeError, ValueError) as exc:
        raise InvalidSchedule("legacy numeric field is invalid") from exc
    if duration <= 0:
        raise InvalidSchedule("legacy duration must be positive")
    return LegacyRecord(
        str(payload["organization"]),
        str(payload["resource"]),
        str(payload["window_id"]),
        timezone_name,
        str(payload["local_start"]),
        weekday,
        duration,
        priority,
    )


def build_upgrade_plan(payloads):
    records = []
    seen = set()
    duplicates = 0
    for payload in payloads:
        record = parse_legacy_record(payload)
        identity = (
            record.organization,
            record.resource,
            record.window_id,
            record.timezone,
            record.local_start,
            record.weekday,
            record.duration_minutes,
            record.priority,
        )
        if identity in seen:
            duplicates += 1
            continue
        seen.add(identity)
        records.append(record)
    records.sort(
        key=lambda row: (row.organization, row.resource, row.window_id, row.local_start)
    )
    return UpgradePlan(tuple(records), duplicates)


def window_payload(record):
    return {
        "window_id": record.window_id,
        "calendar": "legacy",
        "timezone": record.timezone,
        "priority": record.priority,
        "exceptions": {},
        "rule": {
            "frequency": "weekly",
            "start": record.local_start,
            "weekdays": [record.weekday],
            "duration_minutes": record.duration_minutes,
            "count": 1,
        },
    }

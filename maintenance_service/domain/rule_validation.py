from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from .errors import InvalidSchedule

VALID_FREQUENCIES = frozenset({"weekly", "monthly"})
VALID_WEEKDAYS = frozenset({"MO", "TU", "WE", "TH", "FR", "SA", "SU"})
MAX_DURATION_MINUTES = 60 * 24 * 31
MAX_INTERVAL = 366
MAX_COUNT = 10000


@dataclass(frozen=True)
class ValidatedRule:
    frequency: str
    start: str
    duration_minutes: int
    interval: int
    weekdays: tuple[str, ...]
    count: int | None
    until: str | None

    def as_dict(self):
        value = {
            "frequency": self.frequency,
            "start": self.start,
            "duration_minutes": self.duration_minutes,
            "interval": self.interval,
        }
        if self.weekdays:
            value["weekdays"] = list(self.weekdays)
        if self.count is not None:
            value["count"] = self.count
        if self.until is not None:
            value["until"] = self.until
        return value


def _integer(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool):
        raise InvalidSchedule(f"{name} must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise InvalidSchedule(f"{name} must be an integer") from exc
    if parsed < minimum or parsed > maximum:
        raise InvalidSchedule(f"{name} is outside the supported range")
    return parsed


def _timestamp(value: Any, name: str) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise InvalidSchedule(f"{name} must include a UTC offset")
        return value.isoformat()
    if not isinstance(value, str) or not value.strip():
        raise InvalidSchedule(f"{name} must be an ISO-8601 timestamp")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidSchedule(f"{name} must be an ISO-8601 timestamp") from exc
    return value


def validate_timezone(name: Any) -> str:
    if not isinstance(name, str) or not name:
        raise InvalidSchedule("timezone is required")
    try:
        ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise InvalidSchedule("timezone must be an IANA zone") from exc
    return name


def validate_rule(payload: Mapping[str, Any]) -> ValidatedRule:
    if not isinstance(payload, Mapping):
        raise InvalidSchedule("rule must be an object")
    frequency = str(payload.get("frequency", "")).lower()
    if frequency not in VALID_FREQUENCIES:
        raise InvalidSchedule("frequency must be weekly or monthly")
    start = _timestamp(payload.get("start"), "start")
    duration = _integer(
        payload.get("duration_minutes"), "duration_minutes", 1, MAX_DURATION_MINUTES
    )
    interval = _integer(payload.get("interval", 1), "interval", 1, MAX_INTERVAL)
    count = payload.get("count")
    until = payload.get("until")
    if count is not None and until is not None:
        raise InvalidSchedule("count and until are mutually exclusive")
    parsed_count = _integer(count, "count", 1, MAX_COUNT) if count is not None else None
    parsed_until = _timestamp(until, "until") if until is not None else None
    raw_days = payload.get("weekdays", [])
    if not isinstance(raw_days, list):
        raise InvalidSchedule("weekdays must be a list")
    days = tuple(dict.fromkeys(str(item).upper() for item in raw_days))
    if any(day not in VALID_WEEKDAYS for day in days):
        raise InvalidSchedule("weekdays contains an unsupported value")
    if frequency == "weekly" and not days:
        raise InvalidSchedule("weekly rules require weekdays")
    return ValidatedRule(
        frequency, start, duration, interval, days, parsed_count, parsed_until
    )


def validate_window_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = ("window_id", "timezone", "rule", "effective_from")
    missing = [name for name in required if name not in payload]
    if missing:
        raise InvalidSchedule("missing required fields: " + ", ".join(missing))
    window_id = str(payload["window_id"]).strip()
    if not window_id or len(window_id) > 120:
        raise InvalidSchedule("window_id is invalid")
    calendar = str(payload.get("calendar", "default")).strip()
    if not calendar or len(calendar) > 120:
        raise InvalidSchedule("calendar is invalid")
    priority = _integer(payload.get("priority", 0), "priority", -100000, 100000)
    rule = validate_rule(payload["rule"])
    return {
        "window_id": window_id,
        "calendar": calendar,
        "timezone": validate_timezone(payload["timezone"]),
        "rule": rule.as_dict(),
        "exceptions": payload.get("exceptions", {}),
        "priority": priority,
        "effective_from": _timestamp(payload["effective_from"], "effective_from"),
    }

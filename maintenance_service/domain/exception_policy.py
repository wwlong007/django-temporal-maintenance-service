from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Mapping, Any
from .errors import InvalidSchedule
from .timezone_policy import resolve_local, as_utc

VALID_ACTIONS = frozenset({"include", "exclude", "replace", "cancel"})


@dataclass(frozen=True)
class DateException:
    action: str
    original_start: datetime
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(self):
        if self.action not in VALID_ACTIONS:
            raise InvalidSchedule("unsupported override action")
        if self.action in {"include", "replace"} and (
            self.start is None or self.end is None
        ):
            raise InvalidSchedule("include and replace need an interval")
        if self.start is not None and self.end is not None and self.end <= self.start:
            raise InvalidSchedule("override interval must be positive")


def parse_exception_time(value: Any, timezone_name: str) -> datetime:
    if not isinstance(value, str):
        if isinstance(value, datetime):
            return as_utc(value)
        raise InvalidSchedule("exception timestamp must be ISO-8601")
    return as_utc(resolve_local(value, timezone_name))


def normalize_dates(values: Iterable[Any], timezone_name: str) -> tuple[datetime, ...]:
    parsed = {parse_exception_time(value, timezone_name) for value in values}
    return tuple(sorted(parsed))


def normalize_exception_payload(
    payload: Mapping[str, Any], timezone_name: str, duration_minutes: int
):
    if not isinstance(payload, Mapping):
        raise InvalidSchedule("exceptions must be an object")
    rdates = normalize_dates(payload.get("rdates", []), timezone_name)
    exdates = normalize_dates(payload.get("exdates", []), timezone_name)
    duration = timedelta(minutes=duration_minutes)
    return {
        "rdates": tuple((item, item + duration) for item in rdates),
        "exdates": exdates,
    }


def normalize_override(payload: Mapping[str, Any], timezone_name: str) -> DateException:
    action = str(payload.get("action", "")).lower()
    original_value = payload.get("original_start", payload.get("start"))
    if original_value is None:
        raise InvalidSchedule("original_start is required")
    original = parse_exception_time(original_value, timezone_name)
    start = (
        parse_exception_time(payload["start"], timezone_name)
        if payload.get("start") is not None
        else None
    )
    end = (
        parse_exception_time(payload["end"], timezone_name)
        if payload.get("end") is not None
        else None
    )
    return DateException(action, original, start, end)


def exception_summary(
    payload: Mapping[str, Any], timezone_name: str, duration_minutes: int
) -> dict[str, Any]:
    normalized = normalize_exception_payload(payload, timezone_name, duration_minutes)
    return {
        "rdate_count": len(normalized["rdates"]),
        "exdate_count": len(normalized["exdates"]),
        "rdate_starts": tuple(start for start, _ in normalized["rdates"]),
        "exdate_starts": normalized["exdates"],
    }


def exception_instants(
    payload: Mapping[str, Any], timezone_name: str, duration_minutes: int
) -> tuple[datetime, ...]:
    summary = exception_summary(payload, timezone_name, duration_minutes)
    return tuple(sorted(set(summary["rdate_starts"]) | set(summary["exdate_starts"])))


def has_exception_at(
    payload: Mapping[str, Any],
    timezone_name: str,
    duration_minutes: int,
    instant: datetime,
) -> bool:
    return as_utc(instant) in exception_instants(
        payload, timezone_name, duration_minutes
    )

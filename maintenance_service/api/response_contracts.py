from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class WindowResponse:
    window_id: str
    calendar: str
    timezone: str
    rule: dict
    exceptions: dict
    priority: int
    effective_from: datetime
    version: int
    calendar_revision: int

    def as_dict(self):
        return self.__dict__


def window_response(window, revision):
    return WindowResponse(
        window.window_id,
        window.calendar,
        window.timezone,
        window.rule,
        window.exceptions,
        window.priority,
        window.effective_from,
        window.version,
        revision,
    ).as_dict()


def interval_response(item):
    result = {
        "maintenance": bool(item["maintenance"]),
        "available": bool(item["available"]),
        "start": item["start"],
        "end": item["end"],
    }
    if item.get("source_window_id") is not None:
        result["source_window_id"] = item["source_window_id"]
    return result


def availability_response(snapshot):
    intervals = [interval_response(item) for item in snapshot["intervals"]]
    return {
        "maintenance": [item for item in intervals if item["maintenance"]],
        "available": [item for item in intervals if item["available"]],
        "intervals": intervals,
        "calendar_revision": snapshot["calendar_revision"],
        "next_cursor": snapshot["next_cursor"],
    }


def error_response(detail, status):
    return {"detail": detail, "status": status}


def command_response(name, revision, details):
    return {"command": name, "calendar_revision": revision, "details": details}


def timestamp(value):
    return value.isoformat() if isinstance(value, datetime) else value


def normalize_payload(value):
    if isinstance(value, dict):
        return {key: normalize_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_payload(item) for item in value]
    return timestamp(value)

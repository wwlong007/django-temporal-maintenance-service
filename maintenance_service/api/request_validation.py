from dataclasses import dataclass
from typing import Mapping, Any
from maintenance_service.domain.errors import InvalidSchedule
from maintenance_service.domain.rule_validation import validate_window_payload
from maintenance_service.domain.effective_time import parse_instant


@dataclass(frozen=True)
class RequestContext:
    organization: str
    resource: str
    request_id: str | None = None

    def __post_init__(self):
        if not self.organization or not self.resource:
            raise InvalidSchedule("organization and resource are required")


def window_create(payload: Mapping[str, Any]):
    validated = validate_window_payload(payload)
    validated["effective_from"] = parse_instant(validated["effective_from"])
    return validated


def window_patch(payload: Mapping[str, Any]):
    if "version" not in payload:
        raise InvalidSchedule("version is required")
    try:
        version = int(payload["version"])
    except (TypeError, ValueError) as exc:
        raise InvalidSchedule("version must be an integer") from exc
    if version < 1:
        raise InvalidSchedule("version must be positive")
    allowed = {
        "version",
        "calendar",
        "timezone",
        "rule",
        "exceptions",
        "priority",
        "active",
        "effective_from",
    }
    unknown = set(payload) - allowed
    if unknown:
        raise InvalidSchedule("unknown update fields: " + ", ".join(sorted(unknown)))
    if "effective_from" not in payload:
        raise InvalidSchedule("effective_from is required")
    return {
        **payload,
        "version": version,
        "effective_from": parse_instant(payload["effective_from"]),
    }


def override_create(payload):
    action = str(payload.get("action", "")).lower()
    if action not in {"include", "exclude", "replace", "cancel"}:
        raise InvalidSchedule("override action is invalid")
    if "start" not in payload or "end" not in payload:
        raise InvalidSchedule("override needs start and end")
    try:
        version = int(payload.get("version"))
    except (TypeError, ValueError) as exc:
        raise InvalidSchedule("version is required") from exc
    if version < 1:
        raise InvalidSchedule("version must be positive")
    return {**payload, "action": action, "version": version}


def availability_params(query):
    if "from" not in query or "to" not in query:
        raise InvalidSchedule("from and to are required")
    return {
        key: query.get(key)
        for key in ("from", "to", "timezone", "cursor", "limit", "revision")
        if query.get(key) is not None
    }


def require_content_type(request):
    content_type = request.content_type or ""
    if request.method in {"POST", "PATCH"} and "json" not in content_type:
        raise InvalidSchedule("request content type must be JSON")


def request_identifier(request):
    return request.headers.get("X-Request-ID")


def safe_payload(payload):
    if not isinstance(payload, Mapping):
        raise InvalidSchedule("request body must be an object")
    return dict(payload)


def bool_value(value, name):
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    raise InvalidSchedule(f"{name} must be a boolean")

from dataclasses import dataclass
from typing import Mapping, Any
from maintenance_service.domain.errors import InvalidSchedule
from maintenance_service.domain.rule_validation import validate_window_payload


@dataclass(frozen=True)
class RequestContext:
    organization: str
    resource: str
    request_id: str | None = None

    def __post_init__(self):
        if not self.organization or not self.resource:
            raise InvalidSchedule("organization and resource are required")


def window_create(payload: Mapping[str, Any]):
    return validate_window_payload(payload)


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
    }
    unknown = set(payload) - allowed
    if unknown:
        raise InvalidSchedule("unknown update fields: " + ", ".join(sorted(unknown)))
    return {**payload, "version": version}


def override_create(payload):
    action = str(payload.get("action", "")).lower()
    if action not in {"include", "exclude", "replace", "cancel"}:
        raise InvalidSchedule("override action is invalid")
    if "start" not in payload or "end" not in payload:
        raise InvalidSchedule("override needs start and end")
    return {**payload, "action": action}


def availability_params(query):
    if "from" not in query or "to" not in query:
        raise InvalidSchedule("from and to are required")
    return {
        key: query.get(key)
        for key in ("from", "to", "timezone", "cursor", "limit")
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

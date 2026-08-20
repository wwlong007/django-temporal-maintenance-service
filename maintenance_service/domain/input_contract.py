from dataclasses import dataclass
from typing import Mapping, Any
from .errors import InvalidSchedule


@dataclass(frozen=True)
class FieldSpec:
    name: str
    required: bool = True
    nullable: bool = False

    def validate(self, payload):
        present = self.name in payload
        if self.required and not present:
            raise InvalidSchedule(f"{self.name} is required")
        if present and payload[self.name] is None and not self.nullable:
            raise InvalidSchedule(f"{self.name} may not be null")
        return payload.get(self.name)


def require_mapping(value, name):
    if not isinstance(value, Mapping):
        raise InvalidSchedule(f"{name} must be an object")
    return value


def require_fields(payload, *names):
    require_mapping(payload, "payload")
    for name in names:
        FieldSpec(name).validate(payload)
    return payload


def forbid_unknown(payload, allowed):
    unknown = set(payload) - set(allowed)
    if unknown:
        raise InvalidSchedule("unknown fields: " + ", ".join(sorted(unknown)))
    return payload


def optional_string(payload, name, maximum=255):
    value = payload.get(name)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise InvalidSchedule(f"{name} is invalid")
    return value.strip()


def optional_int(payload, name, minimum=None, maximum=None):
    if name not in payload:
        return None
    try:
        value = int(payload[name])
    except (TypeError, ValueError) as exc:
        raise InvalidSchedule(f"{name} must be an integer") from exc
    if minimum is not None and value < minimum:
        raise InvalidSchedule(f"{name} is too small")
    if maximum is not None and value > maximum:
        raise InvalidSchedule(f"{name} is too large")
    return value


def normalized_keys(payload):
    return tuple(sorted(str(key) for key in payload))


def copy_allowed(payload, allowed):
    return {key: payload[key] for key in allowed if key in payload}

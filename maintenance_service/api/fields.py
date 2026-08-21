from datetime import datetime

from rest_framework import serializers


def parse_offset_text(value):
    if not isinstance(value, str):
        raise serializers.ValidationError("timestamp must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise serializers.ValidationError("invalid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise serializers.ValidationError("timestamp must include an offset")
    return parsed


class WindowIdField(serializers.CharField):
    default_error_messages = {
        "blank": "window_id must not be blank",
        "max_length": "window_id is too long",
    }

    def __init__(self, **kwargs):
        kwargs.setdefault("allow_blank", False)
        kwargs.setdefault("max_length", 120)
        kwargs.setdefault("trim_whitespace", True)
        super().__init__(**kwargs)


class OffsetDateTimeField(serializers.DateTimeField):
    def to_internal_value(self, value):
        parse_offset_text(value)
        return super().to_internal_value(value)


class LocalDateTimeField(serializers.CharField):
    def to_internal_value(self, value):
        parsed = super().to_internal_value(value)
        try:
            local = datetime.fromisoformat(parsed)
        except ValueError as exc:
            raise serializers.ValidationError("invalid local date-time") from exc
        if local.tzinfo is not None:
            raise serializers.ValidationError(
                "local date-time must not include an offset"
            )
        return local.isoformat()


def validate_operation_envelope(value):
    if not isinstance(value, dict):
        raise serializers.ValidationError("operation must be an object")
    operation_type = value.get("type")
    if operation_type not in {"create", "patch"}:
        raise serializers.ValidationError("invalid operation type")
    window_id = value.get("window_id")
    if not isinstance(window_id, str) or not window_id.strip():
        raise serializers.ValidationError("window_id is required")
    return value


def require_unique_window_ids(operations):
    seen = set()
    for operation in operations:
        window_id = operation["window_id"]
        if window_id in seen:
            raise serializers.ValidationError("a window may appear only once")
        seen.add(window_id)
    return operations


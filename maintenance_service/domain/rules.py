from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework.exceptions import ValidationError


REQUIRED_RULE_FIELDS = frozenset(
    {"start", "weekdays", "interval", "duration_minutes"}
)
WEEKDAYS = frozenset({"MO", "TU", "WE", "TH", "FR", "SA", "SU"})
STATE_FIELDS = ("timezone", "rule", "priority", "active")


def parse_local_datetime(value, field="local date-time"):
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value))
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"invalid {field}") from exc
    if parsed.tzinfo is not None:
        raise ValidationError(f"{field} must not include an offset")
    return parsed


def parse_timezone(value):
    if not isinstance(value, str) or not value:
        raise ValidationError("invalid timezone")
    try:
        return ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValidationError("invalid timezone") from exc


def positive_integer(value, field):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValidationError(f"{field} must be positive")
    return value


def validate_weekdays(value):
    if not isinstance(value, list) or not value:
        raise ValidationError("weekdays are required")
    if any(item not in WEEKDAYS for item in value):
        raise ValidationError("invalid weekday")
    if len(set(value)) != len(value):
        raise ValidationError("weekdays must be unique")
    return list(value)


def validate_rule(rule):
    if not isinstance(rule, dict) or not REQUIRED_RULE_FIELDS <= set(rule):
        raise ValidationError("incomplete weekly rule")
    if rule.get("frequency", "weekly") != "weekly":
        raise ValidationError("only weekly rules are supported")
    result = deepcopy(rule)
    result["start"] = parse_local_datetime(rule["start"], "rule start").isoformat()
    result["weekdays"] = validate_weekdays(rule["weekdays"])
    result["interval"] = positive_integer(rule["interval"], "interval")
    result["duration_minutes"] = positive_integer(
        rule["duration_minutes"], "duration_minutes"
    )
    if "count" in rule:
        result["count"] = positive_integer(rule["count"], "count")
    if "until" in rule:
        result["until"] = parse_local_datetime(rule["until"], "until").isoformat()
    if "count" in result and "until" in result:
        raise ValidationError("count and until are mutually exclusive")
    return result


def validate_state(state):
    if not isinstance(state, dict):
        raise ValidationError("window state must be an object")
    missing = [field for field in STATE_FIELDS if field not in state]
    if missing:
        raise ValidationError("incomplete window state")
    parse_timezone(state["timezone"])
    priority = state["priority"]
    if isinstance(priority, bool) or not isinstance(priority, int):
        raise ValidationError("priority must be an integer")
    if not isinstance(state["active"], bool):
        raise ValidationError("active must be a boolean")
    result = deepcopy(state)
    result["rule"] = validate_rule(result["rule"])
    return result


def create_state(values):
    return validate_state(
        {
            "timezone": values["timezone"],
            "rule": values["rule"],
            "priority": values["priority"],
            "active": values.get("active", True),
        }
    )


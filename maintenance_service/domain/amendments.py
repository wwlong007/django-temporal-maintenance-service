from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework.exceptions import ValidationError


REQUIRED_RULE_FIELDS = {"start", "weekdays", "interval", "duration_minutes"}
WEEKDAYS = {"MO", "TU", "WE", "TH", "FR", "SA", "SU"}


def merge_patch(target, patch):
    result = deepcopy(target) if isinstance(target, dict) else {}
    for key, value in patch.items():
        if value is None:
            result.pop(key, None)
        elif isinstance(value, dict):
            result[key] = merge_patch(result.get(key), value)
        else:
            result[key] = deepcopy(value)
    return result


def apply_changes(state, changes):
    result = deepcopy(state)
    for key, value in changes.items():
        if key == "rule":
            result[key] = merge_patch(result.get(key), value)
        else:
            result[key] = deepcopy(value)
    return result


def parse_local(value):
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise ValidationError("invalid local date-time") from exc
    if parsed.tzinfo is not None:
        raise ValidationError("local date-time must not include an offset")
    return parsed


def validate_state(state):
    try:
        zone = ZoneInfo(state["timezone"])
    except (KeyError, ZoneInfoNotFoundError) as exc:
        raise ValidationError("invalid timezone") from exc
    rule = state.get("rule")
    if not isinstance(rule, dict) or not REQUIRED_RULE_FIELDS <= set(rule):
        raise ValidationError("incomplete weekly rule")
    if rule.get("frequency", "weekly") != "weekly":
        raise ValidationError("only weekly rules are supported")
    if not isinstance(rule["weekdays"], list) or not rule["weekdays"]:
        raise ValidationError("weekdays are required")
    if any(value not in WEEKDAYS for value in rule["weekdays"]):
        raise ValidationError("invalid weekday")
    for key in ("interval", "duration_minutes"):
        if isinstance(rule[key], bool) or not isinstance(rule[key], int) or rule[key] <= 0:
            raise ValidationError(f"{key} must be positive")
    if "count" in rule:
        if isinstance(rule["count"], bool) or not isinstance(rule["count"], int) or rule["count"] <= 0:
            raise ValidationError("count must be positive")
    if "count" in rule and "until" in rule:
        raise ValidationError("count and until are mutually exclusive")
    start = parse_local(rule["start"])
    start.replace(tzinfo=zone)
    if "until" in rule:
        parse_local(rule["until"])
    if "priority" not in state or "active" not in state:
        raise ValidationError("incomplete window state")
    return state


def snapshots(rows):
    return [
        (row.effective_from, deepcopy(row.changes), row.committed_revision)
        for row in sorted(rows, key=lambda row: (row.effective_from, row.committed_revision))
    ]

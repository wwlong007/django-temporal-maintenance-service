from dataclasses import dataclass
from typing import Mapping, Any
from .rule_validation import validate_rule
from .errors import InvalidSchedule


@dataclass(frozen=True)
class CanonicalRule:
    frequency: str
    start: str
    duration_minutes: int
    interval: int
    weekdays: tuple[str, ...]
    count: int | None
    until: str | None

    def dictionary(self):
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

    def signature(self):
        return "|".join(
            [
                self.frequency,
                self.start,
                str(self.duration_minutes),
                str(self.interval),
                ",".join(self.weekdays),
                str(self.count or ""),
                str(self.until or ""),
            ]
        )


def canonicalize(payload: Mapping[str, Any]):
    value = validate_rule(payload)
    return CanonicalRule(
        value.frequency,
        value.start,
        value.duration_minutes,
        value.interval,
        value.weekdays,
        value.count,
        value.until,
    )


def serialize(payload):
    return canonicalize(payload).dictionary()


def deserialize(payload):
    return canonicalize(payload)


def equal(left, right):
    return canonicalize(left).signature() == canonicalize(right).signature()


def fingerprint(payload):
    return canonicalize(payload).signature()


def patch_rule(rule, updates):
    merged = dict(rule)
    merged.update(updates)
    return serialize(merged)


def weekly_days(payload):
    rule = canonicalize(payload)
    return rule.weekdays if rule.frequency == "weekly" else tuple()


def finite(payload):
    rule = canonicalize(payload)
    return rule.count is not None or rule.until is not None


def validate_compatible_timezone(rule, timezone_name):
    if not timezone_name:
        raise InvalidSchedule("timezone is required")
    return canonicalize(rule)


def summary(payload):
    rule = canonicalize(payload)
    return {
        "frequency": rule.frequency,
        "interval": rule.interval,
        "duration_minutes": rule.duration_minutes,
        "finite": finite(payload),
        "weekdays": list(rule.weekdays),
    }

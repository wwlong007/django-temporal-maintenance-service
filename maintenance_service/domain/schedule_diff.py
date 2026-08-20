from dataclasses import dataclass
from typing import Any, Mapping

MATERIAL_FIELDS = frozenset({"timezone", "rule", "exceptions", "priority", "active"})
PRESENTATION_FIELDS = frozenset({"calendar"})


@dataclass(frozen=True)
class FieldChange:
    name: str
    before: Any
    after: Any
    material: bool

    def as_dict(self):
        return {
            "field": self.name,
            "before": self.before,
            "after": self.after,
            "material": self.material,
        }


@dataclass(frozen=True)
class ScheduleDiff:
    changes: tuple[FieldChange, ...]

    @property
    def changed(self):
        return bool(self.changes)

    @property
    def needs_rebuild(self):
        return any(change.material for change in self.changes)

    @property
    def changed_fields(self):
        return tuple(change.name for change in self.changes)

    def as_dict(self):
        return {
            "changed": self.changed,
            "needs_rebuild": self.needs_rebuild,
            "changes": [change.as_dict() for change in self.changes],
        }


def normalize(value):
    if isinstance(value, dict):
        return {str(key): normalize(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value


def current_window_values(window):
    return {
        "calendar": window.calendar,
        "timezone": window.timezone,
        "rule": normalize(window.rule),
        "exceptions": normalize(window.exceptions),
        "priority": window.priority,
        "active": window.active,
    }


def diff_window(window, updates: Mapping[str, Any]):
    current = current_window_values(window)
    changes = []
    for name, before in current.items():
        if name not in updates:
            continue
        after = normalize(updates[name])
        if normalize(before) == after:
            continue
        changes.append(FieldChange(name, before, after, name in MATERIAL_FIELDS))
    return ScheduleDiff(tuple(changes))


def applies_to_projection(diff):
    return diff.needs_rebuild


def compact_audit(diff):
    return {
        change.name: {"old": change.before, "new": change.after}
        for change in diff.changes
    }


def merge_patch(current: Mapping[str, Any], patch: Mapping[str, Any]):
    merged = dict(current)
    for key, value in patch.items():
        if value is None:
            merged.pop(key, None)
        elif isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_patch(merged[key], value)
        else:
            merged[key] = value
    return merged


def validate_no_unknown_fields(payload, allowed):
    unknown = sorted(set(payload) - set(allowed))
    if unknown:
        raise ValueError("unknown schedule fields: " + ", ".join(unknown))


def patch_is_idempotent(window, payload):
    return not diff_window(window, payload).changed


def describe_change(diff):
    if not diff.changed:
        return "unchanged"
    if diff.needs_rebuild:
        return "projection-rebuild-required"
    return "metadata-only"

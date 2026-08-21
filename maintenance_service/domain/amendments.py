from copy import deepcopy
from typing import Mapping


def merge_patch(target, patch):
    result = deepcopy(target) if isinstance(target, dict) else {}
    for key, value in patch.items():
        if value is None:
            result.pop(key, None)
        elif isinstance(value, Mapping):
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


def changed_fields(changes):
    return frozenset(changes)


def state_delta(previous, current):
    delta = {}
    for key, value in current.items():
        if key not in previous:
            delta[key] = deepcopy(value)
        elif key == "rule" and isinstance(value, dict):
            nested = object_delta(previous.get(key, {}), value)
            if nested:
                delta[key] = nested
        elif previous[key] != value:
            delta[key] = deepcopy(value)
    for key in previous.keys() - current.keys():
        delta[key] = None
    return delta


def object_delta(previous, current):
    result = {}
    for key, value in current.items():
        if key not in previous or previous[key] != value:
            result[key] = deepcopy(value)
    for key in previous.keys() - current.keys():
        result[key] = None
    return result


def contains_state_fields(changes):
    return any(key in changes for key in ("timezone", "rule", "priority", "active"))


def copy_state(state):
    return {
        "timezone": state["timezone"],
        "rule": deepcopy(state["rule"]),
        "priority": state["priority"],
        "active": state["active"],
    }

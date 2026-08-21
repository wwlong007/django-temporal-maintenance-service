from copy import deepcopy


def state_from_window(window):
    return {
        "timezone": window.timezone,
        "rule": deepcopy(window.rule),
        "priority": window.priority,
        "active": window.active,
    }


def update_window(window, state, effective_from, advance_version=True):
    if advance_version:
        window.version += 1
    window.effective_from = effective_from
    window.timezone = state["timezone"]
    window.rule = deepcopy(state["rule"])
    window.priority = state["priority"]
    window.active = state["active"]
    window.save()
    return window


def projection_matches(window, state, effective_from, version):
    return (
        window.version == version
        and window.effective_from == effective_from
        and state_from_window(window) == state
    )


def projection_payload(window):
    return {
        "window_id": window.window_id,
        "effective_from": window.effective_from,
        "version": window.version,
        **state_from_window(window),
    }


def bulk_projection_payload(windows):
    return [projection_payload(window) for window in windows]

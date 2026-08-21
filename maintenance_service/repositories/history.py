from dataclasses import dataclass

from .ledger import generation_records
from .windows import scope_windows


@dataclass(frozen=True)
class WindowHistory:
    window: object
    records: tuple


def load_window_history(window, revision):
    return WindowHistory(window, tuple(generation_records(window, revision)))


def load_scope_history(scope, revision):
    values = []
    for window in scope_windows(scope):
        history = load_window_history(window, revision)
        if history.records:
            values.append(history)
    return values


def histories_by_window(scope, revision):
    return {
        item.window.window_id: item
        for item in load_scope_history(scope, revision)
    }


def latest_record(history):
    if not history.records:
        return None
    return max(
        history.records,
        key=lambda item: (item.committed_revision, item.window_version),
    )


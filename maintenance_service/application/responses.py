from datetime import datetime, timezone


def utc_text(value):
    if not isinstance(value, datetime):
        return value
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def write_result(window, revision, effective_from):
    return {
        "window_id": window.window_id,
        "effective_from": effective_from,
        "version": window.version,
        "calendar_revision": revision,
    }


def batch_result(results):
    if not results:
        raise ValueError("a batch result requires operations")
    return {
        "calendar_revision": results[-1]["calendar_revision"],
        "results": results,
    }


def serialize_interval(item):
    return {
        key: utc_text(value) if key in {"start", "end"} else value
        for key, value in item.items()
    }


def availability_result(revision, intervals):
    return {
        "calendar_revision": revision,
        "intervals": [serialize_interval(item) for item in intervals],
    }


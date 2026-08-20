from datetime import datetime


def key(window_id, start):
    return f"{window_id}:{start.isoformat()}"


def parse(value):
    window_id, separator, start = value.partition(":")
    if not separator:
        raise ValueError("occurrence key is invalid")
    return window_id, datetime.fromisoformat(start)


def sort_key(value):
    window_id, start = parse(value)
    return start, window_id


def same_window(left, right):
    return parse(left)[0] == parse(right)[0]


def prefix(window_id):
    return f"{window_id}:"


def belongs_to(value, window_id):
    return value.startswith(prefix(window_id))


def deduplicate(keys):
    return tuple(sorted(set(keys), key=sort_key))

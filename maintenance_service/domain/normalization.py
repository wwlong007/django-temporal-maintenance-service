from datetime import timezone


def normalize_interval(start, end):
    start = start.astimezone(timezone.utc)
    end = end.astimezone(timezone.utc)
    if end <= start:
        raise ValueError("interval must be positive")
    return start, end


def deduplicate_occurrences(items):
    unique = {}
    for start, end in items:
        unique[start] = (start, end)
    return sorted(unique.values())

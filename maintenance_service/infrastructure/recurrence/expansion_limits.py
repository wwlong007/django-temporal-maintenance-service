MAX_OCCURRENCES = 10000


def bounded(items):
    result = list(items)
    if len(result) > MAX_OCCURRENCES:
        raise ValueError("recurrence expansion exceeds configured bound")
    return result

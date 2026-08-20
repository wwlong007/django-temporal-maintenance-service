from collections import Counter

_counters = Counter()


def increment(name, amount=1):
    _counters[name] += amount


def snapshot():
    return dict(_counters)

from zoneinfo import ZoneInfo


def load_timezone(name):
    return ZoneInfo(name)

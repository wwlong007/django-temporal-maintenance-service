from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from .errors import InvalidSchedule


def resolve_local(value: str, tz_name: str) -> datetime:
    try:
        naive = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if naive.tzinfo is not None:
            naive = naive.astimezone(ZoneInfo(tz_name)).replace(tzinfo=None)
        zone = ZoneInfo(tz_name)
        candidates = [naive.replace(tzinfo=zone, fold=f) for f in (0, 1)]
        valid = [
            c
            for c in candidates
            if c.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == naive
        ]
        if not valid:
            raise InvalidSchedule("local time does not exist in timezone")
        return valid[0]
    except (ValueError, KeyError) as exc:
        raise InvalidSchedule("invalid timestamp or timezone") from exc


def as_utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc)

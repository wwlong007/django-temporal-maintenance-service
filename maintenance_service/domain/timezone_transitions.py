from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from .errors import InvalidSchedule


@dataclass(frozen=True)
class LocalResolution:
    local: datetime
    zone: str
    candidates: tuple[datetime, ...]
    nonexistent: bool
    ambiguous: bool

    def utc_candidates(self):
        return tuple(
            candidate.astimezone(timezone.utc) for candidate in self.candidates
        )

    def offsets(self):
        return tuple(candidate.utcoffset() for candidate in self.candidates)


def local_candidates(local_value, zone_name):
    if local_value.tzinfo is not None:
        local_value = local_value.replace(tzinfo=None)
    try:
        zone = ZoneInfo(zone_name)
    except Exception as exc:
        raise InvalidSchedule("timezone must be an IANA zone") from exc
    candidates = []
    for fold in (0, 1):
        candidate = local_value.replace(tzinfo=zone, fold=fold)
        round_trip = (
            candidate.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None)
        )
        if round_trip == local_value and candidate not in candidates:
            candidates.append(candidate)
    return LocalResolution(
        local_value, zone_name, tuple(candidates), not candidates, len(candidates) > 1
    )


def parse_local(value, zone_name):
    if not isinstance(value, str):
        raise InvalidSchedule("local timestamp must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidSchedule("local timestamp is invalid") from exc
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(ZoneInfo(zone_name)).replace(tzinfo=None)
    return local_candidates(parsed, zone_name)


def transition_summary(value, zone_name):
    resolved = parse_local(value, zone_name)
    return {
        "timezone": zone_name,
        "local": resolved.local.isoformat(),
        "nonexistent": resolved.nonexistent,
        "ambiguous": resolved.ambiguous,
        "utc_candidates": [item.isoformat() for item in resolved.utc_candidates()],
    }


def offsets_between(start, end, zone_name):
    if start >= end:
        return tuple()
    zone = ZoneInfo(zone_name)
    cursor = start.astimezone(timezone.utc)
    result = []
    offset = None
    while cursor < end:
        current = cursor.astimezone(zone).utcoffset()
        if current != offset:
            result.append((cursor, current))
            offset = current
        cursor += timedelta(hours=1)
    return tuple(result)


def crosses_transition(start, end, zone_name):
    return len(offsets_between(start, end, zone_name)) > 1


def transition_candidates(value, zone_name):
    resolved = parse_local(value, zone_name)
    if resolved.nonexistent:
        raise InvalidSchedule("local time does not exist in timezone")
    return resolved.utc_candidates()


def requires_disambiguation(value, zone_name):
    return parse_local(value, zone_name).ambiguous

from dataclasses import dataclass
from datetime import datetime, timezone

from .rules import parse_local_datetime, parse_timezone


@dataclass(frozen=True)
class LocalBinding:
    local: datetime
    instant: datetime
    fold: int


def attach_local(value, timezone_name, fold=0):
    local = parse_local_datetime(value)
    zone = parse_timezone(timezone_name)
    aware = local.replace(tzinfo=zone, fold=fold)
    return LocalBinding(local, aware.astimezone(timezone.utc), fold)


def start_instant(value, timezone_name):
    return attach_local(value, timezone_name).instant


def end_instant(value, timezone_name):
    return attach_local(value, timezone_name).instant


def round_trip(binding, timezone_name):
    zone = parse_timezone(timezone_name)
    return binding.instant.astimezone(zone).replace(tzinfo=None)


def binding_matches(binding, timezone_name):
    return round_trip(binding, timezone_name) == binding.local


def possible_bindings(value, timezone_name):
    first = attach_local(value, timezone_name, fold=0)
    second = attach_local(value, timezone_name, fold=1)
    values = []
    for item in (first, second):
        if binding_matches(item, timezone_name) and item.instant not in {
            candidate.instant for candidate in values
        }:
            values.append(item)
    return values


def is_ambiguous(value, timezone_name):
    return len(possible_bindings(value, timezone_name)) == 2


def exists(value, timezone_name):
    return bool(possible_bindings(value, timezone_name))


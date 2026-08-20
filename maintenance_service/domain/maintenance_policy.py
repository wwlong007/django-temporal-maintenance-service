from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from django.utils.dateparse import parse_datetime

from maintenance_service.domain.errors import InvalidSchedule


MAX_POLICY_MEMBERS = 200


@dataclass(frozen=True)
class PolicyMember:
    resource: str
    zone: str


@dataclass(frozen=True)
class PolicyValues:
    policy_id: str
    effective_from: datetime
    max_unavailable: int
    minimum_available_zones: int
    members: tuple[PolicyMember, ...]
    active: bool

    def as_dict(self):
        return {
            "policy_id": self.policy_id,
            "effective_from": self.effective_from,
            "max_unavailable": self.max_unavailable,
            "minimum_available_zones": self.minimum_available_zones,
            "members": [member.__dict__ for member in self.members],
            "active": self.active,
        }


def policy_instant(value: Any) -> datetime:
    parsed = value if isinstance(value, datetime) else parse_datetime(str(value or ""))
    if parsed is None or parsed.tzinfo is None:
        raise InvalidSchedule("effective_from must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def policy_members(value: Any) -> tuple[PolicyMember, ...]:
    if not isinstance(value, list) or len(value) < 2:
        raise InvalidSchedule("members must contain at least two resources")
    if len(value) > MAX_POLICY_MEMBERS:
        raise InvalidSchedule("maintenance policy has too many members")
    members = []
    resources = set()
    for item in value:
        if not isinstance(item, Mapping):
            raise InvalidSchedule("policy member must be an object")
        resource = str(item.get("resource", "")).strip()
        zone = str(item.get("zone", "")).strip()
        if not resource or not zone or resource in resources:
            raise InvalidSchedule("policy members must identify unique resources and zones")
        resources.add(resource)
        members.append(PolicyMember(resource, zone))
    return tuple(sorted(members, key=lambda member: member.resource))


def validate_policy(payload: Mapping[str, Any], *, policy_id: str | None = None):
    if not isinstance(payload, Mapping):
        raise InvalidSchedule("maintenance policy must be an object")
    selected_id = str(policy_id or payload.get("policy_id", "")).strip()
    if not selected_id:
        raise InvalidSchedule("policy_id is required")
    members = policy_members(payload.get("members"))
    try:
        maximum = int(payload.get("max_unavailable"))
        minimum_zones = int(payload.get("minimum_available_zones"))
    except (TypeError, ValueError) as exc:
        raise InvalidSchedule("policy limits must be integers") from exc
    zone_count = len({member.zone for member in members})
    if maximum < 0 or maximum >= len(members):
        raise InvalidSchedule("max_unavailable is outside the member range")
    if minimum_zones < 1 or minimum_zones > zone_count:
        raise InvalidSchedule("minimum_available_zones is outside the zone range")
    return PolicyValues(
        selected_id,
        policy_instant(payload.get("effective_from")),
        maximum,
        minimum_zones,
        members,
        bool(payload.get("active", True)),
    )

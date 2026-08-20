import base64
import json
from datetime import timedelta

from django.utils.dateparse import parse_datetime

from maintenance_service.application.planning_revision import (
    current_organization_revision,
)
from maintenance_service.domain.errors import InvalidSchedule, NotFound
from maintenance_service.models import (
    CalendarRevision,
    MaintenancePolicy,
    Occurrence,
    Organization,
    Resource,
)


MAX_IMPACT_DAYS = 366
MAX_IMPACT_PAGE = 500


def impact_range(params):
    start = parse_datetime(str(params.get("from", "")))
    end = parse_datetime(str(params.get("to", "")))
    if start is None or end is None or start.tzinfo is None or end.tzinfo is None:
        raise InvalidSchedule("impact range must contain ISO-8601 instants")
    if end <= start or end - start > timedelta(days=MAX_IMPACT_DAYS):
        raise InvalidSchedule("impact range is outside supported bounds")
    try:
        limit = int(params.get("limit", 100))
    except (TypeError, ValueError) as exc:
        raise InvalidSchedule("limit must be an integer") from exc
    if limit < 1 or limit > MAX_IMPACT_PAGE:
        raise InvalidSchedule("limit is outside supported bounds")
    return start, end, limit


def encode_cursor(payload):
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(value):
    try:
        padded = str(value) + "=" * (-len(str(value)) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()))
        if not isinstance(payload, dict):
            raise ValueError
        return payload
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise InvalidSchedule("impact cursor is invalid") from exc


def resource_occurrences(organization, resource_key, start, end):
    try:
        resource = Resource.objects.get(organization=organization, key=resource_key)
    except Resource.DoesNotExist:
        return ()
    revision = CalendarRevision.objects.filter(
        organization=organization, resource=resource
    ).first()
    if revision is None:
        return ()
    return tuple(
        Occurrence.objects.filter(
            window__organization=organization,
            window__resource=resource,
            revision=revision.value,
            start__lt=end,
            end__gt=start,
        ).values_list("start", "end")
    )


def policy_segments(organization, policy, start, end):
    members = {item["resource"]: item["zone"] for item in policy.members}
    rows = {
        resource: resource_occurrences(organization, resource, start, end)
        for resource in members
    }
    boundaries = {start, end}
    for occurrences in rows.values():
        for row_start, row_end in occurrences:
            boundaries.add(max(start, row_start))
            boundaries.add(min(end, row_end))
    values = []
    ordered = sorted(boundaries)
    for left, right in zip(ordered, ordered[1:]):
        unavailable = sorted(
            resource
            for resource, occurrences in rows.items()
            if any(row_start < right and left < row_end for row_start, row_end in occurrences)
        )
        if not unavailable:
            continue
        available_zones = sorted(
            {
                zone
                for resource, zone in members.items()
                if resource not in unavailable
            }
        )
        compliant = (
            len(unavailable) <= policy.max_unavailable
            and len(available_zones) >= policy.minimum_available_zones
        )
        values.append(
            {
                "start": left,
                "end": right,
                "policy_id": policy.policy_id,
                "unavailable_resources": unavailable,
                "available_zones": available_zones,
                "compliant": compliant,
            }
        )
    return values


def maintenance_impact(organization_key, params):
    try:
        organization = Organization.objects.get(key=organization_key)
    except Organization.DoesNotExist as exc:
        raise NotFound("organization does not exist") from exc
    start, end, limit = impact_range(params)
    current = current_organization_revision(organization)
    requested = params.get("revision")
    revision = current if requested is None else int(requested)
    if revision < 0 or revision > current:
        raise InvalidSchedule("organization revision is unavailable")
    intervals = []
    for policy in MaintenancePolicy.objects.filter(
        organization=organization, active=True
    ).order_by("policy_id"):
        intervals.extend(policy_segments(organization, policy, start, end))
    intervals.sort(key=lambda item: (item["start"], item["end"], item["policy_id"]))
    offset = 0
    if params.get("cursor"):
        cursor = decode_cursor(params["cursor"])
        expected = [revision, start.isoformat(), end.isoformat()]
        if cursor.get("query") != expected:
            raise InvalidSchedule("impact cursor does not match the query")
        offset = int(cursor.get("offset", -1))
    if offset < 0 or offset > len(intervals):
        raise InvalidSchedule("impact cursor is outside the result")
    page = intervals[offset : offset + limit]
    next_cursor = None
    if offset + limit < len(intervals):
        next_cursor = encode_cursor(
            {
                "query": [revision, start.isoformat(), end.isoformat()],
                "offset": offset + limit,
            }
        )
    return {
        "organization_revision": revision,
        "intervals": page,
        "violations": [item for item in page if not item["compliant"]],
        "next_cursor": next_cursor,
    }


def has_violation(organization_key, start, end, revision=None):
    params = {"from": start.isoformat(), "to": end.isoformat(), "limit": 500}
    if revision is not None:
        params["revision"] = revision
    return bool(maintenance_impact(organization_key, params)["violations"])

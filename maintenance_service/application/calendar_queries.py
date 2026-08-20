from django.utils.dateparse import parse_datetime
from maintenance_service.models import (
    Organization,
    Resource,
    Occurrence,
    CalendarRevision,
)
from maintenance_service.domain.conflicts import effective_intervals
from maintenance_service.application.availability_service import (
    parse_query,
    build_snapshot,
)
from maintenance_service.application.projection_snapshot import ProjectionSnapshotReader
from maintenance_service.infrastructure.observability.metrics import increment
from maintenance_service.infrastructure.observability.structured_logging import event


def availability(org_key, resource_key, start_value, end_value, cursor=0):
    org = Organization.objects.get(key=org_key)
    resource = Resource.objects.get(organization=org, key=resource_key)
    start, end = parse_datetime(start_value), parse_datetime(end_value)
    revision = CalendarRevision.objects.get(organization=org, resource=resource).value
    rows = list(
        Occurrence.objects.filter(
            window__organization=org,
            window__resource=resource,
            start__lt=end,
            end__gt=start,
        ).values_list("start", "end", "priority", "source")
    )
    out = []
    point = start
    for interval, priority, source in effective_intervals(rows):
        if interval.end <= start or interval.start >= end:
            continue
        s, e = max(interval.start, start), min(interval.end, end)
        if point < s:
            out.append(
                {"maintenance": False, "available": True, "start": point, "end": s}
            )
        out.append(
            {
                "maintenance": True,
                "available": False,
                "start": s,
                "end": e,
                "source_window_id": source,
            }
        )
        point = max(point, e)
    if point < end:
        out.append(
            {"maintenance": False, "available": True, "start": point, "end": end}
        )
    offset = int(cursor or 0)
    page = out[offset : offset + 100]
    return page, revision, str(offset + 100) if offset + 100 < len(out) else None


def availability_snapshot(org_key, resource_key, params):
    query = parse_query(params)
    projection = ProjectionSnapshotReader().read(
        org_key, resource_key, query.start, query.end
    )
    snapshot = build_snapshot(projection.rows, query, projection.revision)
    increment("calendar.availability.read")
    event(
        "calendar.availability.read",
        organization=org_key,
        resource=resource_key,
        revision=projection.revision,
        intervals=len(snapshot["intervals"]),
    )
    return snapshot

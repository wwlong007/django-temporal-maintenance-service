from datetime import timezone

from rest_framework.exceptions import ValidationError

from maintenance_service.domain.amendments import snapshots
from maintenance_service.domain.intervals import partition
from maintenance_service.domain.recurrence import expand_weekly
from maintenance_service.models import CalendarRevision, MaintenanceWindow


def availability(organization_key, resource_key, query):
    revision_row = CalendarRevision.objects.filter(
        organization__key=organization_key,
        resource__key=resource_key,
    ).first()
    current = revision_row.value if revision_row else 0
    revision = query.get("revision", current)
    if revision > current:
        raise ValidationError("revision is not available")
    start = query["from"].astimezone(timezone.utc)
    end = query["to"].astimezone(timezone.utc)
    values = []
    windows = MaintenanceWindow.objects.filter(
        organization__key=organization_key, resource__key=resource_key
    )
    for window in windows:
        rows = window.generations.filter(committed_revision__lte=revision)
        states = snapshots(rows)
        for index, (effective_from, state, _) in enumerate(states):
            if not state["active"]:
                continue
            next_effective = states[index + 1][0] if index + 1 < len(states) else None
            for occurrence_start, occurrence_end in expand_weekly(state, start, end):
                if occurrence_start < effective_from:
                    continue
                if next_effective is not None and occurrence_start >= next_effective:
                    continue
                values.append(
                    (
                        occurrence_start,
                        occurrence_end,
                        state["priority"],
                        window.window_id,
                    )
                )
    intervals = partition(start, end, values)
    return {
        "calendar_revision": revision,
        "intervals": [serialize(item) for item in intervals],
    }


def serialize(item):
    return {
        key: value.isoformat().replace("+00:00", "Z") if key in {"start", "end"} else value
        for key, value in item.items()
    }

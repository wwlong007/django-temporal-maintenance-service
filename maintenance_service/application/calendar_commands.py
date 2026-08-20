from django.db import transaction
from maintenance_service.models import (
    Organization,
    Resource,
    MaintenanceWindow,
    CalendarRevision,
    Override,
    WindowGeneration,
)
from maintenance_service.domain.errors import VersionConflict
from maintenance_service.domain.rule_validation import validate_window_payload
from maintenance_service.domain.exception_policy import normalize_exception_payload
from maintenance_service.domain.schedule_diff import diff_window, compact_audit
from maintenance_service.infrastructure.observability.structured_logging import event
from maintenance_service.infrastructure.observability.metrics import increment
from maintenance_service.application.occurrence_service import rebuild_window
from maintenance_service.application.planning_revision import publish_resource_revision


def get_scope(org_key, resource_key):
    org, _ = Organization.objects.get_or_create(key=org_key, defaults={"name": org_key})
    resource, _ = Resource.objects.get_or_create(
        organization=org, key=resource_key, defaults={"name": resource_key}
    )
    return org, resource


def increment_revision(org, resource):
    rev, _ = CalendarRevision.objects.select_for_update().get_or_create(
        organization=org, resource=resource
    )
    rev.value += 1
    rev.save(update_fields=["value", "updated_at"])
    return rev.value


@transaction.atomic
def create_window(org_key, resource_key, data):
    data = validate_window_payload(data)
    normalized = normalize_exception_payload(
        data.get("exceptions", {}),
        data["timezone"],
        int(data["rule"]["duration_minutes"]),
    )
    data["exceptions"] = {
        "rdates": [start.isoformat() for start, _ in normalized["rdates"]],
        "exdates": [value.isoformat() for value in normalized["exdates"]],
    }
    org, resource = get_scope(org_key, resource_key)
    window = MaintenanceWindow.objects.create(
        organization=org,
        resource=resource,
        window_id=data["window_id"],
        calendar=data.get("calendar", "default"),
        timezone=data["timezone"],
        rule=data["rule"],
        exceptions=data.get("exceptions", {}),
        priority=data.get("priority", 0),
        effective_from=data["effective_from"],
    )
    revision = increment_revision(org, resource)
    WindowGeneration.objects.create(
        window=window,
        effective_from=window.effective_from,
        calendar=window.calendar,
        timezone=window.timezone,
        rule=window.rule,
        exceptions=window.exceptions,
        priority=window.priority,
        active=window.active,
        window_version=window.version,
        committed_revision=revision,
    )
    rebuild_window(window, revision)
    publish_resource_revision(org, resource, revision)
    increment("calendar.window.created")
    event(
        "calendar.window.created",
        organization=org_key,
        resource=resource_key,
        window_id=window.window_id,
        revision=revision,
    )
    return window, revision


@transaction.atomic
def update_window(org_key, resource_key, window_id, data):
    org, resource = get_scope(org_key, resource_key)
    window = MaintenanceWindow.objects.get(
        organization=org, resource=resource, window_id=window_id
    )
    if int(data.get("version", -1)) != window.version:
        raise VersionConflict("version conflict")
    if "rule" in data or "timezone" in data:
        candidate = {
            "window_id": window.window_id,
            "calendar": data.get("calendar", window.calendar),
            "timezone": data.get("timezone", window.timezone),
            "rule": data.get("rule", window.rule),
            "exceptions": data.get("exceptions", window.exceptions),
            "priority": data.get("priority", window.priority),
            "effective_from": data["effective_from"],
        }
        data = {**data, **validate_window_payload(candidate)}
    change = diff_window(window, data)
    for field in (
        "calendar",
        "timezone",
        "rule",
        "exceptions",
        "priority",
        "active",
        "effective_from",
    ):
        if field in data:
            setattr(window, field, data[field])
    window.version += 1
    window.save()
    revision = increment_revision(org, resource)
    WindowGeneration.objects.create(
        window=window,
        effective_from=window.effective_from,
        calendar=window.calendar,
        timezone=window.timezone,
        rule=window.rule,
        exceptions=window.exceptions,
        priority=window.priority,
        active=window.active,
        window_version=window.version,
        committed_revision=revision,
    )
    rebuild_window(window, revision)
    publish_resource_revision(org, resource, revision)
    increment("calendar.window.updated")
    event(
        "calendar.window.updated",
        organization=org_key,
        resource=resource_key,
        window_id=window_id,
        revision=revision,
        changes=compact_audit(change),
    )
    return window, revision


@transaction.atomic
def add_override(org_key, resource_key, window_id, data):
    org, resource = get_scope(org_key, resource_key)
    window = MaintenanceWindow.objects.select_for_update().get(
        organization=org, resource=resource, window_id=window_id
    )
    if int(data.get("version", -1)) != window.version:
        raise VersionConflict("version conflict")
    revision = increment_revision(org, resource)
    Override.objects.create(
        window=window,
        original_start=data.get("original_start", data["start"]),
        action=data["action"],
        start=data["start"],
        end=data["end"],
        window_version=window.version + 1,
        committed_revision=revision,
    )
    window.version += 1
    window.save(update_fields=["version"])
    rebuild_window(window, revision)
    publish_resource_revision(org, resource, revision)
    increment("calendar.override.created")
    event(
        "calendar.override.created",
        organization=org_key,
        resource=resource_key,
        window_id=window_id,
        revision=revision,
    )
    return window, revision

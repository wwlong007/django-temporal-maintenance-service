from copy import deepcopy

from django.db import transaction
from django.shortcuts import get_object_or_404

from maintenance_service.api.errors import Conflict
from maintenance_service.domain.amendments import apply_changes, snapshots, validate_state
from maintenance_service.models import (
    CalendarRevision,
    MaintenanceWindow,
    Organization,
    Resource,
    WindowGeneration,
)


def get_scope(organization_key, resource_key):
    organization, _ = Organization.objects.get_or_create(
        key=organization_key, defaults={"name": organization_key}
    )
    resource, _ = Resource.objects.get_or_create(
        organization=organization,
        key=resource_key,
        defaults={"name": resource_key},
    )
    return organization, resource


def next_revision(organization, resource):
    row, _ = CalendarRevision.objects.get_or_create(
        organization=organization, resource=resource
    )
    row.value += 1
    row.save(update_fields=["value", "updated_at"])
    return row.value


def response(window, revision):
    return {
        "window_id": window.window_id,
        "effective_from": window.effective_from,
        "version": window.version,
        "calendar_revision": revision,
    }


@transaction.atomic
def create_window(organization_key, resource_key, data):
    organization, resource = get_scope(organization_key, resource_key)
    state = validate_state(
        {
            "timezone": data["timezone"],
            "rule": deepcopy(data["rule"]),
            "priority": data["priority"],
            "active": data.get("active", True),
        }
    )
    window = MaintenanceWindow.objects.create(
        organization=organization,
        resource=resource,
        window_id=data["window_id"],
        effective_from=data["effective_from"],
        **state,
    )
    revision = next_revision(organization, resource)
    WindowGeneration.objects.create(
        window=window,
        effective_from=data["effective_from"],
        changes=state,
        window_version=1,
        committed_revision=revision,
    )
    return response(window, revision)


@transaction.atomic
def patch_window(organization_key, resource_key, window_id, data):
    organization, resource = get_scope(organization_key, resource_key)
    window = get_object_or_404(
        MaintenanceWindow,
        organization=organization,
        resource=resource,
        window_id=window_id,
    )
    if data["version"] != window.version:
        raise Conflict()
    rows = snapshots(window.generations.all())
    inherited = {}
    for effective_from, state, _ in rows:
        if effective_from <= data["effective_from"]:
            inherited = state
    changes = {
        key: deepcopy(data[key])
        for key in ("timezone", "rule", "priority", "active")
        if key in data
    }
    state = validate_state(apply_changes(inherited, changes))
    revision = next_revision(organization, resource)
    window.version += 1
    window.effective_from = data["effective_from"]
    window.timezone = state["timezone"]
    window.rule = state["rule"]
    window.priority = state["priority"]
    window.active = state["active"]
    window.save()
    WindowGeneration.objects.create(
        window=window,
        effective_from=data["effective_from"],
        changes=state,
        window_version=window.version,
        committed_revision=revision,
    )
    return response(window, revision)

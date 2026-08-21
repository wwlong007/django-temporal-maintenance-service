from copy import deepcopy

from django.db import transaction
from django.shortcuts import get_object_or_404

from maintenance_service.api.errors import Conflict
from maintenance_service.domain.amendments import apply_changes, snapshots, validate_state
from maintenance_service.models import MaintenanceWindow
from maintenance_service.repositories.commits import record_commit
from maintenance_service.repositories.ledger import append_generation
from maintenance_service.repositories.projections import update_window
from maintenance_service.repositories.scopes import get_or_create_scope


def get_scope(organization_key, resource_key):
    organization, resource, _ = get_or_create_scope(organization_key, resource_key)
    return organization, resource


def next_revision(organization, resource):
    _, _, row = get_or_create_scope(organization.key, resource.key)
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
    generation = append_generation(window, data["effective_from"], state, 1, revision)
    record_commit(organization, resource, revision, window, generation, "create")
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
    update_window(window, state, data["effective_from"])
    generation = append_generation(
        window, data["effective_from"], state, window.version, revision
    )
    record_commit(organization, resource, revision, window, generation, "patch")
    return response(window, revision)

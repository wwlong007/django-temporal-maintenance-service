from dataclasses import dataclass
from datetime import datetime, timezone
from django.db import transaction
from maintenance_service.models import (
    Organization,
    Resource,
    MaintenanceWindow,
    CalendarRevision,
    Occurrence,
)
from maintenance_service.domain.errors import NotFound, InvalidSchedule
from maintenance_service.domain.revision_policy import stable_snapshot
from maintenance_service.infrastructure.observability.audit_events import (
    calendar_changed,
)
from maintenance_service.infrastructure.observability.structured_logging import event


@dataclass(frozen=True)
class ResourceIdentity:
    organization: str
    resource: str


@dataclass(frozen=True)
class WindowState:
    identity: ResourceIdentity
    window_id: str
    version: int
    calendar_revision: int
    active: bool
    occurrence_count: int

    def as_dict(self):
        return {
            "organization": self.identity.organization,
            "resource": self.identity.resource,
            "window_id": self.window_id,
            "version": self.version,
            "calendar_revision": self.calendar_revision,
            "active": self.active,
            "occurrence_count": self.occurrence_count,
        }


def get_resource(identity: ResourceIdentity):
    try:
        organization = Organization.objects.get(key=identity.organization)
        return organization, Resource.objects.get(
            organization=organization, key=identity.resource
        )
    except (Organization.DoesNotExist, Resource.DoesNotExist) as exc:
        raise NotFound("resource does not exist") from exc


def get_window(identity: ResourceIdentity, window_id: str, lock=False):
    organization, resource = get_resource(identity)
    query = MaintenanceWindow.objects
    if lock:
        query = query.select_for_update()
    try:
        return (
            organization,
            resource,
            query.get(
                organization=organization, resource=resource, window_id=window_id
            ),
        )
    except MaintenanceWindow.DoesNotExist as exc:
        raise NotFound("maintenance window does not exist") from exc


def revision_for(organization, resource, lock=False):
    query = CalendarRevision.objects
    if lock:
        query = query.select_for_update()
    try:
        return query.get(organization=organization, resource=resource)
    except CalendarRevision.DoesNotExist as exc:
        raise NotFound("calendar revision does not exist") from exc


def state_for(identity, window_id):
    organization, resource, window = get_window(identity, window_id)
    revision = revision_for(organization, resource)
    return WindowState(
        identity,
        window.window_id,
        window.version,
        revision.value,
        window.active,
        Occurrence.objects.filter(window=window, revision=revision.value).count(),
    )


@transaction.atomic
def deactivate(identity, window_id, expected_version):
    organization, resource, window = get_window(identity, window_id, lock=True)
    if window.version != int(expected_version):
        raise InvalidSchedule("version conflict")
    if not window.active:
        return state_for(identity, window_id)
    window.active = False
    window.version += 1
    window.save(update_fields=["active", "version"])
    revision = revision_for(organization, resource, lock=True)
    revision.value += 1
    revision.save(update_fields=["value", "updated_at"])
    Occurrence.objects.filter(window=window).delete()
    event(
        "calendar.window.deactivated",
        organization=identity.organization,
        resource=identity.resource,
        window_id=window_id,
        revision=revision.value,
    )
    calendar_changed(identity.organization, identity.resource)
    return WindowState(identity, window_id, window.version, revision.value, False, 0)


@transaction.atomic
def activate(identity, window_id, expected_version, rebuild):
    organization, resource, window = get_window(identity, window_id, lock=True)
    if window.version != int(expected_version):
        raise InvalidSchedule("version conflict")
    if window.active:
        return state_for(identity, window_id)
    window.active = True
    window.version += 1
    window.save(update_fields=["active", "version"])
    revision = revision_for(organization, resource, lock=True)
    revision.value += 1
    revision.save(update_fields=["value", "updated_at"])
    rebuild(window, revision.value)
    event(
        "calendar.window.activated",
        organization=identity.organization,
        resource=identity.resource,
        window_id=window_id,
        revision=revision.value,
    )
    return state_for(identity, window_id)


def snapshot_for(identity, window_id):
    state = state_for(identity, window_id)
    return stable_snapshot(state.calendar_revision, state.version)


def validate_identity(organization, resource):
    if not isinstance(organization, str) or not organization.strip():
        raise InvalidSchedule("organization is required")
    if not isinstance(resource, str) or not resource.strip():
        raise InvalidSchedule("resource is required")
    if len(organization) > 100 or len(resource) > 100:
        raise InvalidSchedule("resource identity is too long")
    return ResourceIdentity(organization.strip(), resource.strip())


def window_summary(identity):
    organization, resource = get_resource(identity)
    revision = revision_for(organization, resource)
    windows = MaintenanceWindow.objects.filter(
        organization=organization, resource=resource
    ).order_by("window_id")
    return {
        "organization": identity.organization,
        "resource": identity.resource,
        "calendar_revision": revision.value,
        "windows": [
            {
                "window_id": item.window_id,
                "version": item.version,
                "active": item.active,
                "priority": item.priority,
                "updated_at": item.id,
            }
            for item in windows
        ],
    }


def current_time():
    return datetime.now(timezone.utc)

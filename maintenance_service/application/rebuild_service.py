from django.db import transaction
from maintenance_service.models import (
    Organization,
    Resource,
    MaintenanceWindow,
    CalendarRevision,
)
from maintenance_service.application.occurrence_service import rebuild_window
from maintenance_service.infrastructure.persistence.projection_repository import (
    ProjectionRepository,
)


@transaction.atomic
def rebuild_resource(organization_key, resource_key):
    organization = Organization.objects.get(key=organization_key)
    resource = Resource.objects.get(organization=organization, key=resource_key)
    revision = CalendarRevision.objects.select_for_update().get(
        organization=organization, resource=resource
    )
    windows = list(
        MaintenanceWindow.objects.select_for_update().filter(
            organization=organization, resource=resource, active=True
        )
    )
    for window in windows:
        rebuild_window(window, revision.value)
    return {
        "organization": organization_key,
        "resource": resource_key,
        "windows": len(windows),
        "revision": revision.value,
    }


def rebuild_with_projection_repository(organization_key, resource_key):
    organization = Organization.objects.get(key=organization_key)
    resource = Resource.objects.get(organization=organization, key=resource_key)
    repository = ProjectionRepository()
    revision = repository.current_revision(organization, resource, lock=True)
    rebuilt = 0
    for window in repository.lock_windows(organization, resource):
        rebuild_window(window, revision.value)
        rebuilt += 1
    repository.delete_stale(organization, resource, revision.value)
    return {"revision": revision.value, "rebuilt": rebuilt}

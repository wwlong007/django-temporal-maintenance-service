from dataclasses import dataclass
from django.db import transaction, IntegrityError
from maintenance_service.models import (
    Organization,
    Resource,
    MaintenanceWindow,
    CalendarRevision,
    Override,
)
from maintenance_service.domain.errors import NotFound, VersionConflict


@dataclass(frozen=True)
class Scope:
    organization: Organization
    resource: Resource


class CalendarRepository:
    def get_or_create_scope(self, organization_key, resource_key):
        organization, _ = Organization.objects.get_or_create(
            key=organization_key, defaults={"name": organization_key}
        )
        resource, _ = Resource.objects.get_or_create(
            organization=organization, key=resource_key, defaults={"name": resource_key}
        )
        return Scope(organization, resource)

    def find_scope(self, organization_key, resource_key):
        try:
            organization = Organization.objects.get(key=organization_key)
            return Scope(
                organization,
                Resource.objects.get(organization=organization, key=resource_key),
            )
        except (Organization.DoesNotExist, Resource.DoesNotExist) as exc:
            raise NotFound("resource does not exist") from exc

    def revision(self, scope, lock=False):
        query = CalendarRevision.objects
        if lock:
            query = query.select_for_update()
        value, _ = query.get_or_create(
            organization=scope.organization, resource=scope.resource
        )
        return value

    def list_windows(self, scope, active=None, lock=False):
        query = MaintenanceWindow.objects.filter(
            organization=scope.organization, resource=scope.resource
        ).order_by("id")
        if active is not None:
            query = query.filter(active=active)
        if lock:
            query = query.select_for_update()
        return list(query)

    def window(self, scope, window_id, lock=False):
        query = MaintenanceWindow.objects
        if lock:
            query = query.select_for_update()
        try:
            return query.get(
                organization=scope.organization,
                resource=scope.resource,
                window_id=window_id,
            )
        except MaintenanceWindow.DoesNotExist as exc:
            raise NotFound("maintenance window does not exist") from exc

    def create_window(self, scope, values):
        return MaintenanceWindow.objects.create(
            organization=scope.organization, resource=scope.resource, **values
        )

    def save_window(self, window, fields=None):
        window.save(update_fields=fields)

    def overrides(self, window):
        return list(
            Override.objects.filter(window=window).order_by("original_start", "id")
        )

    def add_override(self, window, values):
        return Override.objects.create(window=window, **values)

    def increment_revision(self, scope):
        revision = self.revision(scope, lock=True)
        revision.value += 1
        revision.save(update_fields=["value", "updated_at"])
        return revision

    @transaction.atomic
    def compare_and_update(self, scope, window_id, expected_version, changes):
        window = self.window(scope, window_id, lock=True)
        if window.version != expected_version:
            raise VersionConflict("version conflict")
        for field, value in changes.items():
            setattr(window, field, value)
        window.version += 1
        window.save()
        revision = self.increment_revision(scope)
        return window, revision

    def exists(self, scope, window_id):
        return MaintenanceWindow.objects.filter(
            organization=scope.organization,
            resource=scope.resource,
            window_id=window_id,
        ).exists()

    def remove_window(self, scope, window_id):
        return self.window(scope, window_id, lock=True).delete()

    def counts(self, scope):
        windows = MaintenanceWindow.objects.filter(
            organization=scope.organization, resource=scope.resource
        )
        return {
            "windows": windows.count(),
            "active_windows": windows.filter(active=True).count(),
            "overrides": Override.objects.filter(window__in=windows).count(),
        }

    def scopes_for_organization(self, organization_key):
        try:
            organization = Organization.objects.get(key=organization_key)
        except Organization.DoesNotExist:
            return []
        return [
            Scope(organization, resource)
            for resource in Resource.objects.filter(organization=organization).order_by(
                "key"
            )
        ]

    def transactional_scope(self, organization_key, resource_key):
        return self.get_or_create_scope(organization_key, resource_key)

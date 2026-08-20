from dataclasses import dataclass
from django.db import transaction
from maintenance_service.models import LegacySchedule, Organization, Resource
from maintenance_service.domain.errors import NotFound


@dataclass(frozen=True)
class LegacyRow:
    legacy_id: str
    organization: str
    resource: str
    local_start: object
    weekday: int
    timezone: str
    migrated_at: object


class LegacyRepository:
    def create(self, organization, resource, legacy_id, local_start, weekday, timezone):
        return LegacySchedule.objects.create(
            organization=organization,
            resource=resource,
            legacy_id=legacy_id,
            local_start=local_start,
            weekday=weekday,
            timezone=timezone,
        )

    def list_for_scope(self, organization, resource):
        return [
            LegacyRow(
                row.legacy_id,
                organization.key,
                resource.key,
                row.local_start,
                row.weekday,
                row.timezone,
                row.migrated_at,
            )
            for row in LegacySchedule.objects.filter(
                organization=organization, resource=resource
            ).order_by("legacy_id", "id")
        ]

    def pending(self, organization=None):
        query = LegacySchedule.objects.filter(migrated_at__isnull=True)
        if organization is not None:
            query = query.filter(organization=organization)
        return query.order_by("organization_id", "resource_id", "id")

    def mark_migrated(self, row, at):
        row.migrated_at = at
        row.save(update_fields=["migrated_at"])

    @transaction.atomic
    def mark_all(self, rows, at):
        count = 0
        for row in rows:
            self.mark_migrated(row, at)
            count += 1
        return count

    def find_scope(self, organization_key, resource_key):
        try:
            organization = Organization.objects.get(key=organization_key)
            return organization, Resource.objects.get(
                organization=organization, key=resource_key
            )
        except (Organization.DoesNotExist, Resource.DoesNotExist) as exc:
            raise NotFound("legacy scope does not exist") from exc

    def count_pending(self):
        return LegacySchedule.objects.filter(migrated_at__isnull=True).count()

    def delete_scope(self, organization, resource):
        return LegacySchedule.objects.filter(
            organization=organization, resource=resource
        ).delete()[0]

    def identities(self):
        return tuple(
            LegacySchedule.objects.values_list(
                "organization__key", "resource__key", "legacy_id"
            ).order_by("organization__key", "resource__key", "legacy_id")
        )

    def duplicates(self):
        seen = set()
        duplicates = []
        for value in self.identities():
            if value in seen:
                duplicates.append(value)
            seen.add(value)
        return tuple(duplicates)

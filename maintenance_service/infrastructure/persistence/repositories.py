from maintenance_service.models import (
    Organization,
    Resource,
    MaintenanceWindow,
    Occurrence,
)


class CalendarRepository:
    def scope(self, organization_key, resource_key):
        organization = Organization.objects.get(key=organization_key)
        resource = Resource.objects.get(organization=organization, key=resource_key)
        return organization, resource

    def windows(self, organization, resource):
        return MaintenanceWindow.objects.filter(
            organization=organization, resource=resource, active=True
        )


class OccurrenceRepository:
    def for_range(self, organization, resource, start, end):
        return Occurrence.objects.filter(
            window__organization=organization,
            window__resource=resource,
            start__lt=end,
            end__gt=start,
        ).order_by("start", "id")

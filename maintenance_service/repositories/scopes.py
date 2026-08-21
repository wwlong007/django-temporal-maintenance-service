from maintenance_service.models import CalendarRevision, Organization, Resource


def get_or_create_scope(organization_key, resource_key):
    organization, _ = Organization.objects.get_or_create(
        key=organization_key, defaults={"name": organization_key}
    )
    resource, _ = Resource.objects.get_or_create(
        organization=organization,
        key=resource_key,
        defaults={"name": resource_key},
    )
    revision, _ = CalendarRevision.objects.get_or_create(
        organization=organization, resource=resource
    )
    return organization, resource, revision

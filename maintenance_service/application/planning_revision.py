from maintenance_service.models import (
    OrganizationRevision,
    ResourceRevisionCommit,
)


def current_organization_revision(organization):
    row, _ = OrganizationRevision.objects.get_or_create(organization=organization)
    return row.value


def advance_organization_revision(organization, resource_revisions=()):
    row, _ = OrganizationRevision.objects.get_or_create(organization=organization)
    row.value += 1
    row.save(update_fields=["value", "updated_at"])
    for resource, calendar_revision in resource_revisions:
        ResourceRevisionCommit.objects.create(
            organization=organization,
            resource=resource,
            organization_revision=row.value,
            calendar_revision=calendar_revision,
        )
    return row.value


def publish_resource_revision(organization, resource, calendar_revision):
    return advance_organization_revision(
        organization, ((resource, calendar_revision),)
    )


def calendar_revision_at(organization, resource, organization_revision):
    row = (
        ResourceRevisionCommit.objects.filter(
            organization=organization,
            resource=resource,
            organization_revision__lte=organization_revision,
        )
        .order_by("-organization_revision")
        .first()
    )
    return row.calendar_revision if row is not None else 0

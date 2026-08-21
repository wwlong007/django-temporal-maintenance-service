from dataclasses import dataclass

from django.db import IntegrityError

from maintenance_service.models import CalendarRevision, Organization, Resource


@dataclass(frozen=True)
class ScopeRows:
    organization: Organization
    resource: Resource
    revision: CalendarRevision

    @property
    def current_revision(self):
        return self.revision.value


def get_or_create_organization(key):
    return Organization.objects.get_or_create(key=key, defaults={"name": key})[0]


def get_or_create_resource(organization, key):
    return Resource.objects.get_or_create(
        organization=organization,
        key=key,
        defaults={"name": key},
    )[0]


def get_or_create_revision(organization, resource):
    return CalendarRevision.objects.get_or_create(
        organization=organization,
        resource=resource,
        defaults={"value": 0},
    )[0]


def get_or_create_scope(organization_key, resource_key):
    organization = get_or_create_organization(organization_key)
    resource = get_or_create_resource(organization, resource_key)
    revision = get_or_create_revision(organization, resource)
    return ScopeRows(organization, resource, revision)


def find_scope(organization_key, resource_key):
    revision = (
        CalendarRevision.objects.select_related("organization", "resource")
        .filter(
            organization__key=organization_key,
            resource__key=resource_key,
            resource__organization__key=organization_key,
        )
        .first()
    )
    if revision is None:
        return None
    return ScopeRows(revision.organization, revision.resource, revision)


def allocate_revision(scope):
    scope.revision.value += 1
    scope.revision.save(update_fields=["value", "updated_at"])
    return scope.revision.value


def refresh_scope(scope):
    row = CalendarRevision.objects.get(pk=scope.revision.pk)
    return ScopeRows(scope.organization, scope.resource, row)


def create_scope(organization_key, resource_key):
    try:
        return get_or_create_scope(organization_key, resource_key)
    except IntegrityError:
        return get_or_create_scope(organization_key, resource_key)


def scope_filter(scope):
    return {
        "organization": scope.organization,
        "resource": scope.resource,
    }

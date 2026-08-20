from dataclasses import dataclass
from django.db import transaction
from maintenance_service.models import CalendarRevision, Occurrence, MaintenanceWindow
from maintenance_service.domain.errors import InvalidSchedule
from maintenance_service.infrastructure.persistence.projection_repository import (
    assert_single_revision,
    ProjectionRepository,
)


@dataclass(frozen=True)
class ConsistencyReport:
    organization: str
    resource: str
    revision: int
    occurrence_count: int
    stale_count: int
    active_window_count: int
    valid: bool

    def as_dict(self):
        return self.__dict__


def inspect(organization, resource):
    revision = CalendarRevision.objects.get(
        organization=organization, resource=resource
    )
    occurrences = Occurrence.objects.filter(
        window__organization=organization, window__resource=resource
    )
    stale = occurrences.exclude(revision=revision.value).count()
    active = MaintenanceWindow.objects.filter(
        organization=organization, resource=resource, active=True
    ).count()
    return ConsistencyReport(
        organization.key,
        resource.key,
        revision.value,
        occurrences.count(),
        stale,
        active,
        stale == 0,
    )


def assert_consistent(organization, resource):
    report = inspect(organization, resource)
    if not report.valid:
        raise InvalidSchedule("calendar projection has stale occurrences")
    return report


@transaction.atomic
def repair_stale(organization, resource):
    repository = ProjectionRepository()
    revision = repository.current_revision(organization, resource, lock=True)
    removed = repository.delete_stale(organization, resource, revision.value)
    return {"revision": revision.value, "removed": removed}


def revision_rows(organization, resource):
    return list(
        Occurrence.objects.filter(
            window__organization=organization, window__resource=resource
        ).values_list("start", "end", "priority", "source", "revision")
    )


def assert_rows(organization, resource):
    revision = CalendarRevision.objects.get(
        organization=organization, resource=resource
    )
    rows = revision_rows(organization, resource)
    from maintenance_service.infrastructure.persistence.projection_repository import (
        ProjectionRow,
    )

    assert_single_revision([ProjectionRow(*row) for row in rows], revision.value)
    return revision.value


def count_by_revision(organization, resource):
    output = {}
    for revision in Occurrence.objects.filter(
        window__organization=organization, window__resource=resource
    ).values_list("revision", flat=True):
        output[revision] = output.get(revision, 0) + 1
    return output


def expected_active_sources(organization, resource):
    return set(
        MaintenanceWindow.objects.filter(
            organization=organization, resource=resource, active=True
        ).values_list("window_id", flat=True)
    )


def projected_sources(organization, resource, revision):
    return set(
        Occurrence.objects.filter(
            window__organization=organization,
            window__resource=resource,
            revision=revision,
        ).values_list("source", flat=True)
    )


def missing_sources(organization, resource):
    revision = CalendarRevision.objects.get(
        organization=organization, resource=resource
    ).value
    return expected_active_sources(organization, resource) - projected_sources(
        organization, resource, revision
    )


def diagnostics(organization, resource):
    report = inspect(organization, resource)
    return {
        **report.as_dict(),
        "revisions": count_by_revision(organization, resource),
        "missing_sources": sorted(missing_sources(organization, resource)),
    }

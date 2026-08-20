from dataclasses import dataclass
from datetime import datetime
from maintenance_service.application.calendar_lifecycle import validate_identity
from maintenance_service.infrastructure.persistence.calendar_repository import (
    CalendarRepository,
)
from maintenance_service.infrastructure.persistence.occurrence_repository import (
    OccurrenceRepository,
)
from maintenance_service.domain.calendar_composition import compose, count_by_source
from maintenance_service.domain.conflict_policy import diagnose
from maintenance_service.domain.availability_policy import AvailabilityRange


@dataclass(frozen=True)
class CalendarReport:
    organization: str
    resource: str
    revision: int
    window_count: int
    occurrence_count: int
    conflict_count: int
    sources: dict

    def as_dict(self):
        return {
            "organization": self.organization,
            "resource": self.resource,
            "calendar_revision": self.revision,
            "window_count": self.window_count,
            "occurrence_count": self.occurrence_count,
            "conflict_count": self.conflict_count,
            "sources": self.sources,
        }


def report(organization, resource, start, end):
    identity = validate_identity(organization, resource)
    scope = CalendarRepository().find_scope(identity.organization, identity.resource)
    revision = CalendarRepository().revision(scope)
    values = OccurrenceRepository().for_scope_range(scope, start, end, revision.value)
    rows = [
        (value.start, value.end, value.priority, value.source, value.revision)
        for value in values
    ]
    return CalendarReport(
        identity.organization,
        identity.resource,
        revision.value,
        len(CalendarRepository().list_windows(scope)),
        len(rows),
        len(diagnose(rows)),
        count_by_source(rows),
    )


def maintenance_summary(organization, resource, start, end):
    requested = AvailabilityRange(start, end)
    data = report(organization, resource, start, end)
    scope = CalendarRepository().find_scope(organization, resource)
    revision = CalendarRepository().revision(scope)
    rows = [
        (value.start, value.end, value.priority, value.source, value.revision)
        for value in OccurrenceRepository().for_scope_range(
            scope, start, end, revision.value
        )
    ]
    composition = compose(rows)
    maintenance = composition.maintenance_for(start, end)
    available = composition.available_for(start, end)
    return {
        **data.as_dict(),
        "requested_seconds": requested.duration.total_seconds(),
        "maintenance_seconds": sum(
            (item.interval.end - item.interval.start).total_seconds()
            for item in maintenance
        ),
        "available_seconds": sum(
            (item.end - item.start).total_seconds() for item in available
        ),
        "effective_intervals": len(maintenance),
    }


def window_report(organization, resource, window_id, start, end):
    scope = CalendarRepository().find_scope(organization, resource)
    window = CalendarRepository().window(scope, window_id)
    revision = CalendarRepository().revision(scope)
    rows = OccurrenceRepository().for_scope_range(scope, start, end, revision.value)
    own = [row for row in rows if row.source == window_id]
    return {
        "window_id": window_id,
        "version": window.version,
        "priority": window.priority,
        "active": window.active,
        "occurrences": len(own),
        "calendar_revision": revision.value,
        "first_start": own[0].start if own else None,
        "last_end": own[-1].end if own else None,
    }


def all_reports(organization, start, end):
    repository = CalendarRepository()
    return [
        report(organization, scope.resource.key, start, end).as_dict()
        for scope in repository.scopes_for_organization(organization)
    ]


def health(organization, resource):
    scope = CalendarRepository().find_scope(organization, resource)
    revision = CalendarRepository().revision(scope)
    occurrences = OccurrenceRepository()
    return {
        "calendar_revision": revision.value,
        "mixed_revisions": occurrences.has_mixed_revisions(scope, revision.value),
        "occurrences": occurrences.count(scope),
        "windows": CalendarRepository().counts(scope),
    }


def compare_reports(before, after):
    keys = set(before) | set(after)
    return {
        key: {"before": before.get(key), "after": after.get(key)}
        for key in keys
        if before.get(key) != after.get(key)
    }

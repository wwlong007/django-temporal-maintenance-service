"""Application-level selection and diagnostics for occurrence projections."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from maintenance_service.domain.errors import InvalidSchedule, NotFound
from maintenance_service.models import (
    CalendarRevision,
    Occurrence,
    Organization,
    Resource,
)


@dataclass(frozen=True)
class ProjectionScope:
    organization: Organization
    resource: Resource

    @property
    def label(self) -> str:
        return f"{self.organization.key}/{self.resource.key}"


@dataclass(frozen=True)
class ProjectionRead:
    scope: ProjectionScope
    revision: int
    rows: tuple[tuple[datetime, datetime, int, str, int], ...]

    @property
    def row_count(self) -> int:
        return len(self.rows)

    def sources(self) -> frozenset[str]:
        return frozenset(row[3] for row in self.rows)


@dataclass(frozen=True)
class ProjectionSummary:
    revision: int
    row_count: int
    source_count: int
    first_start: datetime | None
    last_end: datetime | None

    @classmethod
    def from_read(cls, projection: ProjectionRead) -> "ProjectionSummary":
        starts = tuple(row[0] for row in projection.rows)
        ends = tuple(row[1] for row in projection.rows)
        return cls(
            revision=projection.revision,
            row_count=projection.row_count,
            source_count=len(projection.sources()),
            first_start=min(starts) if starts else None,
            last_end=max(ends) if ends else None,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "revision": self.revision,
            "row_count": self.row_count,
            "source_count": self.source_count,
            "first_start": self.first_start,
            "last_end": self.last_end,
        }


class ProjectionSnapshotReader:
    """Loads occurrence rows that belong to one organization/resource revision."""

    def scope(self, organization_key: str, resource_key: str) -> ProjectionScope:
        try:
            organization = Organization.objects.get(key=organization_key)
            resource = Resource.objects.get(organization=organization, key=resource_key)
        except (Organization.DoesNotExist, Resource.DoesNotExist) as exc:
            raise NotFound("resource does not exist") from exc
        return ProjectionScope(organization, resource)

    def revision(self, scope: ProjectionScope) -> int:
        try:
            return CalendarRevision.objects.get(
                organization=scope.organization,
                resource=scope.resource,
            ).value
        except CalendarRevision.DoesNotExist as exc:
            raise NotFound("calendar revision does not exist") from exc

    def rows(
        self,
        scope: ProjectionScope,
        start: datetime,
        end: datetime,
        revision: int,
    ) -> tuple[tuple[datetime, datetime, int, str, int], ...]:
        if end <= start:
            raise InvalidSchedule("projection query must have a positive range")
        queryset = (
            Occurrence.objects.filter(
                window__organization=scope.organization,
                window__resource=scope.resource,
                window__active=True,
                start__lt=end,
                end__gt=start,
                revision=revision,
            )
            .order_by("start", "end", "id")
            .values_list("start", "end", "priority", "source", "revision")
        )
        return tuple(queryset)

    def read(
        self,
        organization_key: str,
        resource_key: str,
        start: datetime,
        end: datetime,
        revision: int | None = None,
    ) -> ProjectionRead:
        scope = self.scope(organization_key, resource_key)
        current = self.revision(scope)
        selected = current if revision is None else revision
        if selected < 0 or selected > current:
            raise InvalidSchedule("calendar revision is unavailable")
        return ProjectionRead(scope, selected, self.rows(scope, start, end, selected))

    def read_many(
        self,
        scopes: Iterable[tuple[str, str]],
        start: datetime,
        end: datetime,
    ) -> tuple[ProjectionRead, ...]:
        return tuple(
            self.read(organization, resource, start, end)
            for organization, resource in scopes
        )

    def summarize(
        self,
        organization_key: str,
        resource_key: str,
        start: datetime,
        end: datetime,
    ) -> ProjectionSummary:
        return ProjectionSummary.from_read(
            self.read(organization_key, resource_key, start, end)
        )

    def summarize_many(
        self,
        scopes: Iterable[tuple[str, str]],
        start: datetime,
        end: datetime,
    ) -> tuple[ProjectionSummary, ...]:
        reads = self.read_many(scopes, start, end)
        return tuple(ProjectionSummary.from_read(projection) for projection in reads)


def read_projection(
    organization_key: str,
    resource_key: str,
    start: datetime,
    end: datetime,
) -> ProjectionRead:
    return ProjectionSnapshotReader().read(organization_key, resource_key, start, end)


def summarize_projection(
    organization_key: str,
    resource_key: str,
    start: datetime,
    end: datetime,
) -> ProjectionSummary:
    return ProjectionSnapshotReader().summarize(
        organization_key, resource_key, start, end
    )

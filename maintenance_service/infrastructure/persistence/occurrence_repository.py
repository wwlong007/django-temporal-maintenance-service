from dataclasses import dataclass
from datetime import datetime
from django.db import transaction
from maintenance_service.models import Occurrence


@dataclass(frozen=True)
class PersistedOccurrence:
    start: datetime
    end: datetime
    priority: int
    source: str
    revision: int


class OccurrenceRepository:
    def replace(self, window, revision, intervals):
        Occurrence.objects.filter(window=window).delete()
        records = [
            Occurrence(
                window=window,
                start=start,
                end=end,
                span=(start, end),
                priority=window.priority,
                source=window.window_id,
                revision=revision,
            )
            for start, end in intervals
        ]
        Occurrence.objects.bulk_create(records, batch_size=500)
        return len(records)

    def for_scope_range(self, scope, start, end, revision=None):
        query = Occurrence.objects.filter(
            window__organization=scope.organization,
            window__resource=scope.resource,
            window__active=True,
            start__lt=end,
            end__gt=start,
        )
        if revision is not None:
            query = query.filter(revision=revision)
        return [
            PersistedOccurrence(*row)
            for row in query.order_by("start", "end", "id").values_list(
                "start", "end", "priority", "source", "revision"
            )
        ]

    def delete_for_window(self, window):
        return Occurrence.objects.filter(window=window).delete()[0]

    def delete_stale(self, scope, revision):
        return (
            Occurrence.objects.filter(
                window__organization=scope.organization, window__resource=scope.resource
            )
            .exclude(revision=revision)
            .delete()[0]
        )

    def count(self, scope, revision=None):
        query = Occurrence.objects.filter(
            window__organization=scope.organization, window__resource=scope.resource
        )
        if revision is not None:
            query = query.filter(revision=revision)
        return query.count()

    def revision_set(self, scope):
        return set(
            Occurrence.objects.filter(
                window__organization=scope.organization, window__resource=scope.resource
            ).values_list("revision", flat=True)
        )

    def has_mixed_revisions(self, scope, revision):
        return (
            Occurrence.objects.filter(
                window__organization=scope.organization, window__resource=scope.resource
            )
            .exclude(revision=revision)
            .exists()
        )

    @transaction.atomic
    def replace_many(self, windows, revision, expand):
        total = 0
        for window in windows:
            total += self.replace(window, revision, expand(window))
        return total

    def first_after(self, scope, instant):
        return (
            Occurrence.objects.filter(
                window__organization=scope.organization,
                window__resource=scope.resource,
                start__gte=instant,
            )
            .order_by("start", "id")
            .first()
        )

    def latest_before(self, scope, instant):
        return (
            Occurrence.objects.filter(
                window__organization=scope.organization,
                window__resource=scope.resource,
                end__lte=instant,
            )
            .order_by("-end", "-id")
            .first()
        )

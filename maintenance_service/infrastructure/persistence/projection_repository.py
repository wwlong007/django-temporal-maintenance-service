from dataclasses import dataclass
from datetime import datetime
from django.db import transaction
from maintenance_service.models import Occurrence, CalendarRevision, MaintenanceWindow


@dataclass(frozen=True)
class ProjectionRow:
    start: datetime
    end: datetime
    priority: int
    source: str
    revision: int


class ProjectionRepository:
    def current_revision(self, organization, resource, lock=False):
        query = CalendarRevision.objects
        if lock:
            query = query.select_for_update()
        revision, _ = query.get_or_create(organization=organization, resource=resource)
        return revision

    def advance_revision(self, organization, resource):
        revision = self.current_revision(organization, resource, lock=True)
        revision.value += 1
        revision.save(update_fields=["value", "updated_at"])
        return revision.value

    def replace_window(self, window, revision, intervals):
        Occurrence.objects.filter(window=window).delete()
        objects = [
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
        Occurrence.objects.bulk_create(objects, batch_size=1000)
        return len(objects)

    def rows_for_range(self, organization, resource, start, end, revision):
        values = (
            Occurrence.objects.filter(
                window__organization=organization,
                window__resource=resource,
                window__active=True,
                start__lt=end,
                end__gt=start,
                revision=revision,
            )
            .order_by("start", "end", "id")
            .values_list("start", "end", "priority", "source", "revision")
        )
        return [ProjectionRow(*row) for row in values]

    def delete_stale(self, organization, resource, revision):
        return (
            Occurrence.objects.filter(
                window__organization=organization, window__resource=resource
            )
            .exclude(revision=revision)
            .delete()[0]
        )

    @transaction.atomic
    def lock_windows(self, organization, resource):
        return list(
            MaintenanceWindow.objects.select_for_update()
            .filter(organization=organization, resource=resource)
            .order_by("id")
        )


class RevisionMismatch(RuntimeError):
    pass


def assert_single_revision(rows, expected):
    revisions = {row.revision for row in rows}
    if revisions and revisions != {expected}:
        raise RevisionMismatch(
            f"projection revisions {sorted(revisions)} do not match {expected}"
        )

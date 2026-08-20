from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime
from maintenance_service.infrastructure.persistence.calendar_repository import (
    CalendarRepository,
)
from maintenance_service.infrastructure.persistence.occurrence_repository import (
    OccurrenceRepository,
)
from maintenance_service.domain.conflict_policy import (
    diagnose,
    no_overlapping_effective_intervals,
)
from maintenance_service.domain.recurrence_limits import validate_expansion_range


class Command(BaseCommand):
    help = "Validate recurrence bounds, occurrence revisions and precedence consistency for a resource."

    def add_arguments(self, parser):
        parser.add_argument("--organization", required=True)
        parser.add_argument("--resource", required=True)
        parser.add_argument("--from", dest="start", required=True)
        parser.add_argument("--to", dest="end", required=True)

    def handle(self, *args, **options):
        start, end = parse_datetime(options["start"]), parse_datetime(options["end"])
        if start is None or end is None:
            raise CommandError("range timestamps are invalid")
        validate_expansion_range(start, end)
        calendars = CalendarRepository()
        occurrences = OccurrenceRepository()
        try:
            scope = calendars.find_scope(options["organization"], options["resource"])
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        revision = calendars.revision(scope)
        rows = [
            (value.start, value.end, value.priority, value.source, value.revision)
            for value in occurrences.for_scope_range(scope, start, end, revision.value)
        ]
        conflicts = diagnose(rows)
        if not no_overlapping_effective_intervals(rows):
            raise CommandError("effective intervals overlap")
        if occurrences.has_mixed_revisions(scope, revision.value):
            raise CommandError("projection has mixed revisions")
        self.stdout.write(
            f"calendar revision={revision.value} rows={len(rows)} conflicts={len(conflicts)}"
        )

import json
from django.core.management.base import BaseCommand, CommandError
from maintenance_service.infrastructure.persistence.calendar_repository import (
    CalendarRepository,
)
from maintenance_service.application.consistency_service import diagnostics
from maintenance_service.application.calendar_lifecycle import validate_identity


class Command(BaseCommand):
    help = (
        "Inspect the current calendar revision and projected maintenance occurrences."
    )

    def add_arguments(self, parser):
        parser.add_argument("--organization", required=True)
        parser.add_argument("--resource", required=True)
        parser.add_argument("--json", action="store_true")
        parser.add_argument("--strict", action="store_true")

    def handle(self, *args, **options):
        identity = validate_identity(options["organization"], options["resource"])
        repository = CalendarRepository()
        try:
            scope = repository.find_scope(identity.organization, identity.resource)
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        report = diagnostics(scope.organization, scope.resource)
        report["counts"] = repository.counts(scope)
        if options["strict"] and (report["stale_count"] or report["missing_sources"]):
            raise CommandError("calendar projection is inconsistent")
        if options["json"]:
            self.stdout.write(json.dumps(report, default=str, sort_keys=True))
        else:
            self.stdout.write(
                f"organization={report['organization']} resource={report['resource']} revision={report['revision']}"
            )
            self.stdout.write(
                f"windows={report['counts']['windows']} active={report['counts']['active_windows']} occurrences={report['occurrence_count']} stale={report['stale_count']}"
            )
            self.stdout.write(
                f"missing_sources={','.join(report['missing_sources']) or '-'}"
            )

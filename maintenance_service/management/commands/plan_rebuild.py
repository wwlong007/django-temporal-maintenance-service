import json
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime
from maintenance_service.infrastructure.persistence.calendar_repository import (
    CalendarRepository,
)
from maintenance_service.application.rebuild_planner import build_plan, describe_plan


class Command(BaseCommand):
    help = (
        "Show the bounded occurrence projection work for a resource without writing it."
    )

    def add_arguments(self, parser):
        parser.add_argument("--organization", required=True)
        parser.add_argument("--resource", required=True)
        parser.add_argument("--from", dest="start", required=True)
        parser.add_argument("--to", dest="end", required=True)
        parser.add_argument("--json", action="store_true")

    def handle(self, *args, **options):
        start, end = parse_datetime(options["start"]), parse_datetime(options["end"])
        if start is None or end is None:
            raise CommandError("rebuild timestamps are invalid")
        repository = CalendarRepository()
        try:
            scope = repository.find_scope(options["organization"], options["resource"])
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        revision = repository.revision(scope)
        windows = repository.list_windows(scope)
        plan = build_plan(
            scope.organization.key,
            scope.resource.key,
            windows,
            start,
            end,
            revision.value,
            "operator-request",
        )
        if options["json"]:
            self.stdout.write(json.dumps(plan.as_dict(), default=str, sort_keys=True))
        else:
            self.stdout.write(describe_plan(plan))

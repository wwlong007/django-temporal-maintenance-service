from django.core.management.base import BaseCommand, CommandError
from maintenance_service.models import (
    Organization,
    Resource,
    MaintenanceWindow,
    CalendarRevision,
)
from django.utils.dateparse import parse_datetime
from maintenance_service.application.occurrence_service import rebuild_window


class Command(BaseCommand):
    def add_arguments(self, p):
        p.add_argument("--organization", required=True)
        p.add_argument("--resource", required=True)
        p.add_argument("--from", dest="start", required=True)
        p.add_argument("--to", dest="end", required=True)
        p.add_argument("--revision", type=int)

    def handle(self, *args, **opts):
        try:
            o = Organization.objects.get(key=opts["organization"])
            r = Resource.objects.get(organization=o, key=opts["resource"])
            rev = CalendarRevision.objects.get(organization=o, resource=r)
            selected_revision = (
                rev.value if opts.get("revision") is None else opts["revision"]
            )
            if selected_revision < 0 or selected_revision > rev.value:
                raise CommandError("revision is unavailable")
            start = parse_datetime(opts["start"])
            end = parse_datetime(opts["end"])
            if start is None or end is None or end <= start:
                raise CommandError("invalid rebuild range")
            for w in MaintenanceWindow.objects.filter(
                organization=o, resource=r, active=True
            ):
                rebuild_window(w, selected_revision, start, end)
            self.stdout.write(f"rebuild complete revision={selected_revision}")
        except Exception as exc:
            raise CommandError(str(exc))

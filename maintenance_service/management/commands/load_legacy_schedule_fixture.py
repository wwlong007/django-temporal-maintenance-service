from django.core.management.base import BaseCommand, CommandError
from maintenance_service.application.legacy_import_service import (
    import_fixture,
    preview_fixture,
)


class Command(BaseCommand):
    help = "Import legacy local-time schedule records as maintenance windows."

    def add_arguments(self, parser):
        parser.add_argument("fixture")

    def handle(self, *args, **options):
        try:
            result = import_fixture(options["fixture"])
            self.stdout.write(
                self.style.SUCCESS(
                    f"imported {result.imported} schedules duplicates={result.duplicates}"
                )
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc

from django.db import migrations


def mark_legacy_rows(apps, schema_editor):
    LegacySchedule = apps.get_model("maintenance_service", "LegacySchedule")
    for row in LegacySchedule.objects.filter(migrated_at__isnull=True).iterator():
        row.migrated_at = row.local_start
        row.save(update_fields=["migrated_at"])


class Migration(migrations.Migration):
    dependencies = [("maintenance_service", "0003_occurrence_projection")]
    operations = [migrations.RunPython(mark_legacy_rows, migrations.RunPython.noop)]

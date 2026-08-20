import datetime

import django.db.models.deletion
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields.ranges import RangeOperators
from django.db import migrations, models


def seed_generations(apps, schema_editor):
    MaintenanceWindow = apps.get_model("maintenance_service", "MaintenanceWindow")
    WindowGeneration = apps.get_model("maintenance_service", "WindowGeneration")
    CalendarRevision = apps.get_model("maintenance_service", "CalendarRevision")
    epoch = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    for window in MaintenanceWindow.objects.order_by("id"):
        revision = (
            CalendarRevision.objects.filter(
                organization_id=window.organization_id,
                resource_id=window.resource_id,
            ).values_list("value", flat=True).first()
            or 0
        )
        window.effective_from = epoch
        window.save(update_fields=["effective_from"])
        WindowGeneration.objects.create(
            window_id=window.id,
            effective_from=epoch,
            calendar=window.calendar,
            timezone=window.timezone,
            rule=window.rule,
            exceptions=window.exceptions,
            priority=window.priority,
            active=window.active,
            window_version=window.version,
            committed_revision=revision,
        )


class Migration(migrations.Migration):
    dependencies = [("maintenance_service", "0006_occurrence_scope_exclusion")]

    operations = [
        migrations.AddField(
            model_name="maintenancewindow",
            name="effective_from",
            field=models.DateTimeField(
                default=datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="override",
            name="committed_revision",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="override",
            name="window_version",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.RemoveConstraint(
            model_name="occurrence", name="occurrence_unique_start"
        ),
        migrations.RemoveConstraint(
            model_name="occurrence", name="occurrence_window_overlap"
        ),
        migrations.CreateModel(
            name="WindowGeneration",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("effective_from", models.DateTimeField()),
                ("calendar", models.CharField(max_length=120)),
                ("timezone", models.CharField(max_length=80)),
                ("rule", models.JSONField(default=dict)),
                ("exceptions", models.JSONField(default=dict)),
                ("priority", models.IntegerField(default=0)),
                ("active", models.BooleanField(default=True)),
                ("window_version", models.PositiveIntegerField()),
                ("committed_revision", models.PositiveIntegerField()),
                (
                    "window",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="generations",
                        to="maintenance_service.maintenancewindow",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["window", "committed_revision", "effective_from"],
                        name="generation_snapshot_lookup",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("window", "effective_from"),
                        name="window_generation_effective_from",
                    ),
                    models.UniqueConstraint(
                        fields=("window", "window_version"),
                        name="window_generation_version",
                    ),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="occurrence",
            constraint=models.UniqueConstraint(
                fields=("window", "revision", "start"),
                name="occurrence_revision_unique_start",
            ),
        ),
        migrations.AddConstraint(
            model_name="occurrence",
            constraint=ExclusionConstraint(
                name="occurrence_revision_window_overlap",
                expressions=[
                    ("window", RangeOperators.EQUAL),
                    ("revision", RangeOperators.EQUAL),
                    ("span", RangeOperators.OVERLAPS),
                ],
            ),
        ),
        migrations.RunPython(seed_generations, migrations.RunPython.noop),
    ]

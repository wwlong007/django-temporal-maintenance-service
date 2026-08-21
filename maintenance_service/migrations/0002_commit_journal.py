import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("maintenance_service", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="CalendarCommit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("revision", models.PositiveIntegerField()),
                ("expected_operations", models.PositiveSmallIntegerField(default=1)),
                ("status", models.CharField(default="published", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="calendar_commits", to="maintenance_service.organization")),
                ("resource", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="calendar_commits", to="maintenance_service.resource")),
            ],
            options={
                "constraints": [models.UniqueConstraint(fields=("organization", "resource", "revision"), name="calendar_commit_scope_revision")]
            },
        ),
        migrations.AddField(
            model_name="windowgeneration",
            name="commit",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="generations", to="maintenance_service.calendarcommit"),
        ),
        migrations.CreateModel(
            name="CalendarCommitOperation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("position", models.PositiveSmallIntegerField()),
                ("operation_type", models.CharField(max_length=12)),
                ("window_version", models.PositiveIntegerField()),
                ("effective_from", models.DateTimeField()),
                ("changes", models.JSONField(default=dict)),
                ("commit", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="operations", to="maintenance_service.calendarcommit")),
                ("window", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="commit_operations", to="maintenance_service.maintenancewindow")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("commit", "position"), name="calendar_commit_operation_position"),
                    models.UniqueConstraint(fields=("commit", "window"), name="calendar_commit_operation_window"),
                ]
            },
        ),
    ]

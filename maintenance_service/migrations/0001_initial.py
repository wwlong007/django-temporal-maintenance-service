import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="Organization",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=100, unique=True)),
                ("name", models.CharField(max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name="Resource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=100)),
                ("name", models.CharField(max_length=200)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="resources", to="maintenance_service.organization")),
            ],
            options={
                "constraints": [models.UniqueConstraint(fields=("organization", "key"), name="resource_org_key")]
            },
        ),
        migrations.CreateModel(
            name="MaintenanceWindow",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("window_id", models.CharField(max_length=120)),
                ("timezone", models.CharField(max_length=80)),
                ("rule", models.JSONField(default=dict)),
                ("priority", models.IntegerField(default=0)),
                ("effective_from", models.DateTimeField()),
                ("version", models.PositiveIntegerField(default=1)),
                ("active", models.BooleanField(default=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="windows", to="maintenance_service.organization")),
                ("resource", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="windows", to="maintenance_service.resource")),
            ],
            options={
                "constraints": [models.UniqueConstraint(fields=("organization", "resource", "window_id"), name="window_scope_id")]
            },
        ),
        migrations.CreateModel(
            name="CalendarRevision",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("value", models.PositiveIntegerField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="revisions", to="maintenance_service.organization")),
                ("resource", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="revisions", to="maintenance_service.resource")),
            ],
            options={
                "constraints": [models.UniqueConstraint(fields=("organization", "resource"), name="revision_scope")]
            },
        ),
        migrations.CreateModel(
            name="WindowGeneration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("effective_from", models.DateTimeField()),
                ("changes", models.JSONField(default=dict)),
                ("window_version", models.PositiveIntegerField()),
                ("committed_revision", models.PositiveIntegerField()),
                ("window", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="generations", to="maintenance_service.maintenancewindow")),
            ],
            options={
                "indexes": [models.Index(fields=["window", "committed_revision", "effective_from"], name="generation_snapshot_lookup")],
                "constraints": [models.UniqueConstraint(fields=("window", "window_version"), name="window_generation_version")],
            },
        ),
    ]

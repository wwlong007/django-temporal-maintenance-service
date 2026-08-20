from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("maintenance_service", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="LegacySchedule",
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
                ("legacy_id", models.CharField(max_length=120)),
                ("local_start", models.DateTimeField()),
                ("weekday", models.PositiveSmallIntegerField()),
                ("timezone", models.CharField(default="UTC", max_length=80)),
                ("migrated_at", models.DateTimeField(null=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="maintenance_service.organization",
                    ),
                ),
                (
                    "resource",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="maintenance_service.resource",
                    ),
                ),
            ],
        )
    ]

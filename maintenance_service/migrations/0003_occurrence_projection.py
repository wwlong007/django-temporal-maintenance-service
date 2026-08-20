from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("maintenance_service", "0002_temporal_calendar_model")]
    operations = [
        migrations.AddIndex(
            model_name="occurrence",
            index=models.Index(
                fields=["window", "start", "end"], name="occurrence_window_range"
            ),
        )
    ]

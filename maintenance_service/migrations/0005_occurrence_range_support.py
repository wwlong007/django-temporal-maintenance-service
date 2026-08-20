from django.db import migrations, models
from django.contrib.postgres.fields import DateTimeRangeField


class Migration(migrations.Migration):
    dependencies = [("maintenance_service", "0004_legacy_schedule_upgrade")]
    operations = [
        migrations.AddField(
            model_name="occurrence", name="span", field=DateTimeRangeField(null=True)
        )
    ]

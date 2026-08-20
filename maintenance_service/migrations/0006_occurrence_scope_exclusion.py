from django.db import migrations
from django.contrib.postgres.operations import BtreeGistExtension
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields.ranges import RangeOperators


class Migration(migrations.Migration):
    dependencies = [("maintenance_service", "0005_occurrence_range_support")]
    operations = [
        BtreeGistExtension(),
        migrations.AddConstraint(
            model_name="occurrence",
            constraint=ExclusionConstraint(
                name="occurrence_window_overlap",
                expressions=[
                    ("window", RangeOperators.EQUAL),
                    ("span", RangeOperators.OVERLAPS),
                ],
            ),
        ),
    ]

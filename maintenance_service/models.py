from django.db import models
from django.contrib.postgres.fields import DateTimeRangeField
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields.ranges import RangeOperators


class Organization(models.Model):
    key = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)


class Resource(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="resources"
    )
    key = models.CharField(max_length=100)
    name = models.CharField(max_length=200)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "key"], name="resource_org_key"
            )
        ]


class MaintenanceWindow(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="windows"
    )
    resource = models.ForeignKey(
        Resource, on_delete=models.CASCADE, related_name="windows"
    )
    window_id = models.CharField(max_length=120)
    calendar = models.CharField(max_length=120)
    timezone = models.CharField(max_length=80)
    rule = models.JSONField(default=dict)
    exceptions = models.JSONField(default=dict)
    priority = models.IntegerField(default=0)
    version = models.PositiveIntegerField(default=1)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "resource", "window_id"], name="window_scope_id"
            )
        ]


class Occurrence(models.Model):
    window = models.ForeignKey(
        MaintenanceWindow, on_delete=models.CASCADE, related_name="occurrences"
    )
    start = models.DateTimeField()
    end = models.DateTimeField()
    priority = models.IntegerField()
    source = models.CharField(max_length=120)
    revision = models.PositiveIntegerField()
    span = DateTimeRangeField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["window", "start"], name="occurrence_unique_start"
            ),
            ExclusionConstraint(
                name="occurrence_window_overlap",
                expressions=[
                    ("window", RangeOperators.EQUAL),
                    ("span", RangeOperators.OVERLAPS),
                ],
            ),
        ]


class Override(models.Model):
    window = models.ForeignKey(
        MaintenanceWindow, on_delete=models.CASCADE, related_name="overrides"
    )
    original_start = models.DateTimeField()
    action = models.CharField(max_length=20)
    start = models.DateTimeField()
    end = models.DateTimeField()


class CalendarRevision(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="revisions"
    )
    resource = models.ForeignKey(
        Resource, on_delete=models.CASCADE, related_name="revisions"
    )
    value = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "resource"], name="revision_scope"
            )
        ]


class LegacySchedule(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    legacy_id = models.CharField(max_length=120)
    local_start = models.DateTimeField()
    weekday = models.PositiveSmallIntegerField()
    timezone = models.CharField(max_length=80, default="UTC")
    migrated_at = models.DateTimeField(null=True)

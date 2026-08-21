from django.db import models


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
    timezone = models.CharField(max_length=80)
    rule = models.JSONField(default=dict)
    priority = models.IntegerField(default=0)
    effective_from = models.DateTimeField()
    version = models.PositiveIntegerField(default=1)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "resource", "window_id"],
                name="window_scope_id",
            )
        ]


class WindowGeneration(models.Model):
    window = models.ForeignKey(
        MaintenanceWindow, on_delete=models.CASCADE, related_name="generations"
    )
    effective_from = models.DateTimeField()
    changes = models.JSONField(default=dict)
    window_version = models.PositiveIntegerField()
    committed_revision = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["window", "window_version"],
                name="window_generation_version",
            )
        ]
        indexes = [
            models.Index(
                fields=["window", "committed_revision", "effective_from"],
                name="generation_snapshot_lookup",
            )
        ]


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

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
    effective_from = models.DateTimeField()
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
        indexes = [
            models.Index(
                fields=["window", "start", "end"], name="occurrence_window_range"
            )
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["window", "revision", "start"],
                name="occurrence_revision_unique_start",
            ),
            ExclusionConstraint(
                name="occurrence_revision_window_overlap",
                expressions=[
                    ("window", RangeOperators.EQUAL),
                    ("revision", RangeOperators.EQUAL),
                    ("span", RangeOperators.OVERLAPS),
                ],
            ),
        ]


class WindowGeneration(models.Model):
    window = models.ForeignKey(
        MaintenanceWindow, on_delete=models.CASCADE, related_name="generations"
    )
    effective_from = models.DateTimeField()
    calendar = models.CharField(max_length=120)
    timezone = models.CharField(max_length=80)
    rule = models.JSONField(default=dict)
    exceptions = models.JSONField(default=dict)
    priority = models.IntegerField(default=0)
    active = models.BooleanField(default=True)
    window_version = models.PositiveIntegerField()
    committed_revision = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["window", "effective_from"],
                name="window_generation_effective_from",
            ),
            models.UniqueConstraint(
                fields=["window", "window_version"],
                name="window_generation_version",
            ),
        ]
        indexes = [
            models.Index(
                fields=["window", "committed_revision", "effective_from"],
                name="generation_snapshot_lookup",
            )
        ]


class Override(models.Model):
    window = models.ForeignKey(
        MaintenanceWindow, on_delete=models.CASCADE, related_name="overrides"
    )
    original_start = models.DateTimeField()
    action = models.CharField(max_length=20)
    start = models.DateTimeField()
    end = models.DateTimeField()
    window_version = models.PositiveIntegerField(default=1)
    committed_revision = models.PositiveIntegerField(default=0)


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


class OrganizationRevision(models.Model):
    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name="planning_revision"
    )
    value = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)


class ResourceRevisionCommit(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="resource_commits"
    )
    resource = models.ForeignKey(
        Resource, on_delete=models.CASCADE, related_name="organization_commits"
    )
    organization_revision = models.PositiveIntegerField()
    calendar_revision = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "resource", "organization_revision"],
                name="resource_commit_revision",
            )
        ]
        indexes = [
            models.Index(
                fields=["organization", "organization_revision", "resource"],
                name="resource_commit_lookup",
            )
        ]


class MaintenancePolicy(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="maintenance_policies"
    )
    policy_id = models.CharField(max_length=120)
    effective_from = models.DateTimeField()
    max_unavailable = models.PositiveIntegerField()
    minimum_available_zones = models.PositiveIntegerField()
    members = models.JSONField(default=list)
    version = models.PositiveIntegerField(default=1)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "policy_id"], name="maintenance_policy_id"
            )
        ]


class PolicyGeneration(models.Model):
    policy = models.ForeignKey(
        MaintenancePolicy, on_delete=models.CASCADE, related_name="generations"
    )
    effective_from = models.DateTimeField()
    max_unavailable = models.PositiveIntegerField()
    minimum_available_zones = models.PositiveIntegerField()
    members = models.JSONField(default=list)
    active = models.BooleanField(default=True)
    policy_version = models.PositiveIntegerField()
    committed_revision = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["policy", "effective_from"],
                name="policy_generation_effective_from",
            ),
            models.UniqueConstraint(
                fields=["policy", "policy_version"],
                name="policy_generation_version",
            ),
        ]
        indexes = [
            models.Index(
                fields=["policy", "committed_revision", "effective_from"],
                name="policy_generation_lookup",
            )
        ]


class MaintenancePlan(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="maintenance_plans"
    )
    plan_id = models.CharField(max_length=120)
    request_fingerprint = models.CharField(max_length=64)
    request_payload = models.JSONField(default=dict)
    response_payload = models.JSONField(default=dict)
    organization_revision = models.PositiveIntegerField()
    committed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "plan_id"], name="maintenance_plan_id"
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

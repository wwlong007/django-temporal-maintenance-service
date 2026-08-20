import django.db.models.deletion
from django.db import migrations, models


def seed_organization_revisions(apps, schema_editor):
    Organization = apps.get_model("maintenance_service", "Organization")
    CalendarRevision = apps.get_model("maintenance_service", "CalendarRevision")
    OrganizationRevision = apps.get_model(
        "maintenance_service", "OrganizationRevision"
    )
    ResourceRevisionCommit = apps.get_model(
        "maintenance_service", "ResourceRevisionCommit"
    )
    for organization in Organization.objects.order_by("id"):
        revisions = list(
            CalendarRevision.objects.filter(organization_id=organization.id).order_by(
                "resource_id"
            )
        )
        value = 1 if revisions else 0
        OrganizationRevision.objects.create(
            organization_id=organization.id,
            value=value,
        )
        if value:
            ResourceRevisionCommit.objects.bulk_create(
                [
                    ResourceRevisionCommit(
                        organization_id=organization.id,
                        resource_id=revision.resource_id,
                        organization_revision=value,
                        calendar_revision=revision.value,
                    )
                    for revision in revisions
                ]
            )


class Migration(migrations.Migration):
    dependencies = [("maintenance_service", "0007_effective_calendar_history")]

    operations = [
        migrations.CreateModel(
            name="OrganizationRevision",
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
                ("value", models.PositiveIntegerField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="planning_revision",
                        to="maintenance_service.organization",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="MaintenancePolicy",
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
                ("policy_id", models.CharField(max_length=120)),
                ("effective_from", models.DateTimeField()),
                ("max_unavailable", models.PositiveIntegerField()),
                ("minimum_available_zones", models.PositiveIntegerField()),
                ("members", models.JSONField(default=list)),
                ("version", models.PositiveIntegerField(default=1)),
                ("active", models.BooleanField(default=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="maintenance_policies",
                        to="maintenance_service.organization",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("organization", "policy_id"),
                        name="maintenance_policy_id",
                    )
                ]
            },
        ),
        migrations.CreateModel(
            name="MaintenancePlan",
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
                ("plan_id", models.CharField(max_length=120)),
                ("request_fingerprint", models.CharField(max_length=64)),
                ("request_payload", models.JSONField(default=dict)),
                ("response_payload", models.JSONField(default=dict)),
                ("organization_revision", models.PositiveIntegerField()),
                ("committed_at", models.DateTimeField(auto_now_add=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="maintenance_plans",
                        to="maintenance_service.organization",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("organization", "plan_id"),
                        name="maintenance_plan_id",
                    )
                ]
            },
        ),
        migrations.CreateModel(
            name="PolicyGeneration",
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
                ("max_unavailable", models.PositiveIntegerField()),
                ("minimum_available_zones", models.PositiveIntegerField()),
                ("members", models.JSONField(default=list)),
                ("active", models.BooleanField(default=True)),
                ("policy_version", models.PositiveIntegerField()),
                ("committed_revision", models.PositiveIntegerField()),
                (
                    "policy",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="generations",
                        to="maintenance_service.maintenancepolicy",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["policy", "committed_revision", "effective_from"],
                        name="policy_generation_lookup",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("policy", "effective_from"),
                        name="policy_generation_effective_from",
                    ),
                    models.UniqueConstraint(
                        fields=("policy", "policy_version"),
                        name="policy_generation_version",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="ResourceRevisionCommit",
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
                ("organization_revision", models.PositiveIntegerField()),
                ("calendar_revision", models.PositiveIntegerField()),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="resource_commits",
                        to="maintenance_service.organization",
                    ),
                ),
                (
                    "resource",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="organization_commits",
                        to="maintenance_service.resource",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["organization", "organization_revision", "resource"],
                        name="resource_commit_lookup",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=(
                            "organization",
                            "resource",
                            "organization_revision",
                        ),
                        name="resource_commit_revision",
                    )
                ],
            },
        ),
        migrations.RunPython(
            seed_organization_revisions,
            migrations.RunPython.noop,
        ),
    ]

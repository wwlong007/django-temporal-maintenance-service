from django.db import transaction

from maintenance_service.application.planning_revision import (
    advance_organization_revision,
)
from maintenance_service.domain.errors import NotFound, VersionConflict
from maintenance_service.domain.maintenance_policy import validate_policy
from maintenance_service.models import (
    MaintenancePolicy,
    Organization,
    PolicyGeneration,
)


def policy_response(policy, revision):
    return {
        "policy_id": policy.policy_id,
        "effective_from": policy.effective_from,
        "max_unavailable": policy.max_unavailable,
        "minimum_available_zones": policy.minimum_available_zones,
        "members": policy.members,
        "active": policy.active,
        "version": policy.version,
        "organization_revision": revision,
    }


def generation_values(policy, revision):
    return {
        "policy": policy,
        "effective_from": policy.effective_from,
        "max_unavailable": policy.max_unavailable,
        "minimum_available_zones": policy.minimum_available_zones,
        "members": policy.members,
        "active": policy.active,
        "policy_version": policy.version,
        "committed_revision": revision,
    }


@transaction.atomic
def create_policy(organization_key, payload):
    values = validate_policy(payload)
    organization, _ = Organization.objects.get_or_create(
        key=organization_key, defaults={"name": organization_key}
    )
    if MaintenancePolicy.objects.filter(
        organization=organization, policy_id=values.policy_id
    ).exists():
        raise VersionConflict("maintenance policy already exists")
    policy = MaintenancePolicy.objects.create(
        organization=organization,
        policy_id=values.policy_id,
        effective_from=values.effective_from,
        max_unavailable=values.max_unavailable,
        minimum_available_zones=values.minimum_available_zones,
        members=[member.__dict__ for member in values.members],
        active=values.active,
    )
    revision = advance_organization_revision(organization)
    PolicyGeneration.objects.create(**generation_values(policy, revision))
    return policy_response(policy, revision)


@transaction.atomic
def update_policy(organization_key, policy_id, payload):
    try:
        organization = Organization.objects.get(key=organization_key)
        policy = MaintenancePolicy.objects.get(
            organization=organization, policy_id=policy_id
        )
    except (Organization.DoesNotExist, MaintenancePolicy.DoesNotExist) as exc:
        raise NotFound("maintenance policy does not exist") from exc
    if int(payload.get("version", -1)) != policy.version:
        raise VersionConflict("version conflict")
    candidate = {
        "policy_id": policy_id,
        "effective_from": payload.get("effective_from"),
        "max_unavailable": payload.get("max_unavailable", policy.max_unavailable),
        "minimum_available_zones": payload.get(
            "minimum_available_zones", policy.minimum_available_zones
        ),
        "members": payload.get("members", policy.members),
        "active": payload.get("active", policy.active),
    }
    values = validate_policy(candidate, policy_id=policy_id)
    if PolicyGeneration.objects.filter(
        policy=policy, effective_from=values.effective_from
    ).exists():
        raise VersionConflict("effective time already exists")
    policy.effective_from = values.effective_from
    policy.max_unavailable = values.max_unavailable
    policy.minimum_available_zones = values.minimum_available_zones
    policy.members = [member.__dict__ for member in values.members]
    policy.active = values.active
    policy.version += 1
    policy.save()
    revision = advance_organization_revision(organization)
    PolicyGeneration.objects.create(**generation_values(policy, revision))
    return policy_response(policy, revision)

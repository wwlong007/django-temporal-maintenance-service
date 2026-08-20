import hashlib
import json
from datetime import timedelta

from django.db import transaction
from django.utils.dateparse import parse_datetime

from maintenance_service.application.calendar_commands import (
    add_override,
    create_window,
    update_window,
)
from maintenance_service.application.maintenance_impact import has_violation
from maintenance_service.application.planning_revision import (
    advance_organization_revision,
)
from maintenance_service.domain.errors import InvalidSchedule, VersionConflict
from maintenance_service.models import (
    CalendarRevision,
    MaintenancePlan,
    Organization,
    Resource,
)


MAX_PLAN_OPERATIONS = 50
MAX_PLAN_DAYS = 366


def canonical_payload(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def fingerprint(payload):
    return hashlib.sha256(canonical_payload(payload).encode()).hexdigest()


def validate_plan(payload):
    if not isinstance(payload, dict):
        raise InvalidSchedule("maintenance plan must be an object")
    plan_id = str(payload.get("plan_id", "")).strip()
    operations = payload.get("operations")
    start = parse_datetime(str(payload.get("from", "")))
    end = parse_datetime(str(payload.get("to", "")))
    if not plan_id:
        raise InvalidSchedule("plan_id is required")
    if start is None or end is None or start.tzinfo is None or end.tzinfo is None:
        raise InvalidSchedule("plan range must contain ISO-8601 instants")
    if end <= start or end - start > timedelta(days=MAX_PLAN_DAYS):
        raise InvalidSchedule("plan range is outside supported bounds")
    if not isinstance(operations, list) or not 1 <= len(operations) <= MAX_PLAN_OPERATIONS:
        raise InvalidSchedule("operations must be a non-empty bounded list")
    targets = set()
    normalized = []
    for item in operations:
        if not isinstance(item, dict):
            raise InvalidSchedule("plan operation must be an object")
        operation = str(item.get("operation", "")).lower()
        resource = str(item.get("resource", "")).strip()
        if operation not in {"create", "patch", "override"} or not resource:
            raise InvalidSchedule("plan operation is invalid")
        if operation == "create":
            body = item.get("window")
            window_id = str(body.get("window_id", "")) if isinstance(body, dict) else ""
        else:
            window_id = str(item.get("window_id", "")).strip()
            body = item.get("changes" if operation == "patch" else "override")
        if not window_id or not isinstance(body, dict):
            raise InvalidSchedule("plan operation target and body are required")
        target = (resource, window_id)
        if target in targets:
            raise InvalidSchedule("a plan may mutate a window only once")
        targets.add(target)
        normalized.append((operation, resource, window_id, body))
    return plan_id, start, end, tuple(normalized)


def execute_operation(organization_key, operation, resource, window_id, body):
    if operation == "create":
        window, revision = create_window(organization_key, resource, body)
    elif operation == "patch":
        window, revision = update_window(
            organization_key, resource, window_id, body
        )
    else:
        window, revision = add_override(
            organization_key, resource, window_id, body
        )
    return {
        "operation": operation,
        "resource": resource,
        "window_id": window.window_id,
        "version": window.version,
        "calendar_revision": revision,
    }


@transaction.atomic
def commit_plan(organization_key, payload):
    plan_id, start, end, operations = validate_plan(payload)
    request_fingerprint = fingerprint(payload)
    organization, _ = Organization.objects.get_or_create(
        key=organization_key, defaults={"name": organization_key}
    )
    existing = MaintenancePlan.objects.filter(
        organization=organization, plan_id=plan_id
    ).first()
    if existing is not None:
        if existing.request_fingerprint != request_fingerprint:
            raise VersionConflict("plan_id already has different content")
        return existing.response_payload
    results = [
        execute_operation(organization_key, operation, resource, window_id, body)
        for operation, resource, window_id, body in operations
    ]
    resource_revisions = {}
    commits = []
    for resource_key in sorted({item[1] for item in operations}):
        resource = Resource.objects.get(
            organization=organization, key=resource_key
        )
        revision = CalendarRevision.objects.get(
            organization=organization, resource=resource
        ).value
        resource_revisions[resource_key] = revision
        commits.append((resource, revision))
    organization_revision = advance_organization_revision(organization, commits)
    if has_violation(organization_key, start, end, organization_revision):
        raise InvalidSchedule("maintenance plan violates an active policy")
    response = {
        "plan_id": plan_id,
        "organization_revision": organization_revision,
        "resource_revisions": resource_revisions,
        "operations": results,
    }
    MaintenancePlan.objects.create(
        organization=organization,
        plan_id=plan_id,
        request_fingerprint=request_fingerprint,
        request_payload=payload,
        response_payload=response,
        organization_revision=organization_revision,
    )
    return response

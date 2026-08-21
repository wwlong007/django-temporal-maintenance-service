from copy import deepcopy

from rest_framework.exceptions import ValidationError

from .amendments import apply_changes
from .rules import STATE_FIELDS, create_state, validate_state
from .types import CommitDraft, OperationDraft, OperationKind


def operation_kind(value):
    try:
        return OperationKind(value)
    except ValueError as exc:
        raise ValidationError("unsupported operation type") from exc


def normalize_create(values):
    state = create_state(values)
    return OperationDraft(
        kind=OperationKind.CREATE,
        window_id=values["window_id"],
        effective_from=values["effective_from"],
        values=state,
    )


def normalize_patch(window_id, values):
    changes = {
        field: deepcopy(values[field])
        for field in STATE_FIELDS
        if field in values
    }
    if not changes:
        raise ValidationError("a state change is required")
    return OperationDraft(
        kind=OperationKind.PATCH,
        window_id=window_id,
        effective_from=values["effective_from"],
        values=changes,
        expected_version=values["version"],
    )


def normalize_batch(operations):
    drafts = []
    seen = set()
    for raw in operations:
        kind = operation_kind(raw["type"])
        window_id = raw["window_id"]
        if window_id in seen:
            raise ValidationError("a window may appear only once")
        seen.add(window_id)
        if kind is OperationKind.CREATE:
            drafts.append(normalize_create(raw))
        else:
            drafts.append(normalize_patch(window_id, raw))
    if not 1 <= len(drafts) <= 32:
        raise ValidationError("a batch requires between one and 32 operations")
    return CommitDraft.from_operations(drafts)


def materialize_patch(draft, inherited):
    if not draft.is_patch:
        return draft
    state = validate_state(apply_changes(inherited, draft.values))
    return draft.with_values(state)


def validate_draft(draft):
    if not draft.window_id or len(draft.window_id) > 120:
        raise ValidationError("invalid window_id")
    if draft.is_create:
        create_state(draft.values)
    elif draft.expected_version is None or draft.expected_version < 1:
        raise ValidationError("version must be positive")
    return draft


def validate_commit_draft(draft):
    if not 1 <= len(draft) <= 32:
        raise ValidationError("invalid operation count")
    if len(set(draft.window_ids)) != len(draft.window_ids):
        raise ValidationError("a window may appear only once")
    for operation in draft.operations:
        validate_draft(operation)
    return draft


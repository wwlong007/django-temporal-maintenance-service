from dataclasses import dataclass

from maintenance_service.api.errors import Conflict
from maintenance_service.domain.operations import materialize_patch, validate_draft
from maintenance_service.domain.rules import create_state
from maintenance_service.domain.timeline import record_from_generation, state_before
from maintenance_service.repositories.ledger import window_generations
from maintenance_service.repositories.windows import require_version


@dataclass(frozen=True)
class PlannedOperation:
    draft: object
    window: object | None
    state: dict
    next_version: int

    @property
    def operation_type(self):
        return self.draft.kind.value


def records_for_window(window):
    return [record_from_generation(row) for row in window_generations(window)]


def inherited_state(window, effective_from):
    return state_before(records_for_window(window), effective_from)


def plan_create(draft):
    validate_draft(draft)
    return PlannedOperation(
        draft=draft,
        window=None,
        state=create_state(draft.values),
        next_version=1,
    )


def plan_patch(draft, window):
    validate_draft(draft)
    require_version(window, draft.expected_version)
    inherited = inherited_state(window, draft.effective_from)
    materialized = materialize_patch(draft, inherited)
    return PlannedOperation(
        draft=materialized,
        window=window,
        state=dict(materialized.values),
        next_version=window.version + 1,
    )


def plan_operation(draft, window=None):
    if draft.is_create:
        if window is not None:
            raise Conflict("window already exists")
        return plan_create(draft)
    if window is None:
        raise LookupError(draft.window_id)
    return plan_patch(draft, window)


def validate_plans(plans):
    ids = [plan.draft.window_id for plan in plans]
    if len(ids) != len(set(ids)):
        raise Conflict("a window may appear only once")
    return plans


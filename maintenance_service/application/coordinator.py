from django.db import transaction

from maintenance_service.domain.commit_protocol import describe_commit
from maintenance_service.domain.operations import validate_commit_draft
from maintenance_service.repositories.commits import record_single
from maintenance_service.repositories.ledger import append_generation
from maintenance_service.repositories.projections import update_window
from maintenance_service.repositories.scopes import allocate_revision, get_or_create_scope
from maintenance_service.repositories.windows import create_window, find_window

from .planning import plan_operation
from .responses import batch_result, write_result


class CommitCoordinator:
    def __init__(self, organization_key, resource_key):
        self.organization_key = organization_key
        self.resource_key = resource_key

    def scope(self):
        return get_or_create_scope(self.organization_key, self.resource_key)

    def plan(self, scope, draft):
        window = find_window(scope, draft.window_id)
        return plan_operation(draft, window)

    def persist(self, scope, plan):
        revision = allocate_revision(scope)
        if plan.draft.is_create:
            window = create_window(scope, plan.draft, plan.state)
            version = 1
        else:
            window = update_window(
                plan.window,
                plan.state,
                plan.draft.effective_from,
                advance_version=True,
            )
            version = window.version
        generation = append_generation(
            window,
            plan.draft.effective_from,
            plan.state,
            version,
            revision,
        )
        record_single(
            scope,
            revision,
            window,
            generation,
            plan.operation_type,
        )
        return write_result(window, revision, plan.draft.effective_from)

    @transaction.atomic
    def commit_one(self, draft):
        scope = self.scope()
        plan = self.plan(scope, draft)
        return self.persist(scope, plan)

    def commit_many(self, commit_draft):
        validate_commit_draft(commit_draft)
        describe_commit(commit_draft)
        results = []
        for draft in commit_draft.operations:
            results.append(self.commit_one(draft))
        return batch_result(results)


def coordinator(organization_key, resource_key):
    return CommitCoordinator(organization_key, resource_key)

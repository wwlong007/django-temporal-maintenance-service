from copy import deepcopy

from maintenance_service.models import CalendarCommit, CalendarCommitOperation


def create_commit(scope, revision, expected_operations=1, status="published"):
    return CalendarCommit.objects.create(
        organization=scope.organization,
        resource=scope.resource,
        revision=revision,
        expected_operations=expected_operations,
        status=status,
    )


def add_operation(commit, window, generation, position, operation_type):
    return CalendarCommitOperation.objects.create(
        commit=commit,
        window=window,
        position=position,
        operation_type=operation_type,
        window_version=generation.window_version,
        effective_from=generation.effective_from,
        changes=deepcopy(generation.changes),
    )


def attach_generation(generation, commit):
    generation.commit = commit
    generation.save(update_fields=["commit"])
    return generation


def record_single(scope, revision, window, generation, operation_type):
    commit = create_commit(scope, revision)
    attach_generation(generation, commit)
    add_operation(commit, window, generation, 0, operation_type)
    return commit


def scope_commits(scope):
    return CalendarCommit.objects.filter(
        organization=scope.organization,
        resource=scope.resource,
    ).order_by("revision")


def visible_commits(scope, revision):
    return scope_commits(scope).filter(revision__lte=revision, status="published")


def commit_at(scope, revision):
    return scope_commits(scope).filter(revision=revision, status="published").first()


def operation_count(commit):
    return commit.operations.count()


def is_complete(commit):
    return commit.status == "published" and operation_count(commit) == commit.expected_operations


def publish(commit):
    commit.status = "published"
    commit.save(update_fields=["status"])
    return commit

from maintenance_service.models import CalendarCommit, CalendarCommitOperation


def record_commit(organization, resource, revision, window, generation, operation_type):
    commit = CalendarCommit.objects.create(
        organization=organization,
        resource=resource,
        revision=revision,
        expected_operations=1,
        status="published",
    )
    generation.commit = commit
    generation.save(update_fields=["commit"])
    CalendarCommitOperation.objects.create(
        commit=commit,
        window=window,
        position=0,
        operation_type=operation_type,
        window_version=generation.window_version,
        effective_from=generation.effective_from,
        changes=generation.changes,
    )
    return commit

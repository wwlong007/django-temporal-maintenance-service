from copy import deepcopy

from maintenance_service.domain.timeline import record_from_generation
from maintenance_service.models import WindowGeneration


def append_generation(window, effective_from, state, version, revision):
    return WindowGeneration.objects.create(
        window=window,
        effective_from=effective_from,
        changes=deepcopy(state),
        window_version=version,
        committed_revision=revision,
    )


def window_generations(window):
    return window.generations.order_by(
        "effective_from", "committed_revision", "window_version"
    )


def visible_generations(window, revision):
    return window_generations(window).filter(committed_revision__lte=revision)


def generation_records(window, revision=None):
    rows = window_generations(window)
    if revision is not None:
        rows = rows.filter(committed_revision__lte=revision)
    return [record_from_generation(row) for row in rows]


def latest_generation(window):
    return window_generations(window).order_by(
        "-committed_revision", "-window_version"
    ).first()


def generation_for_version(window, version):
    return window_generations(window).filter(window_version=version).first()


def scope_generations(scope, revision):
    return (
        WindowGeneration.objects.select_related("window", "commit")
        .filter(
            window__organization=scope.organization,
            window__resource=scope.resource,
            committed_revision__lte=revision,
        )
        .order_by(
            "window_id", "effective_from", "committed_revision", "window_version"
        )
    )


def generation_map(scope, revision):
    result = {}
    for row in scope_generations(scope, revision):
        result.setdefault(row.window_id, []).append(record_from_generation(row))
    return result


def versions_are_contiguous(window):
    versions = list(window_generations(window).values_list("window_version", flat=True))
    return versions == list(range(1, len(versions) + 1))

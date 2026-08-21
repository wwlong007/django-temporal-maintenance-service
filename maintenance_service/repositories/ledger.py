from copy import deepcopy

from maintenance_service.models import WindowGeneration


def append_generation(window, effective_from, state, version, revision):
    return WindowGeneration.objects.create(
        window=window,
        effective_from=effective_from,
        changes=deepcopy(state),
        window_version=version,
        committed_revision=revision,
    )


def visible_generations(window, revision):
    return window.generations.filter(committed_revision__lte=revision)

from copy import deepcopy
from itertools import groupby

from rest_framework.exceptions import ValidationError

from .amendments import apply_changes
from .rules import validate_state
from .types import AmendmentRecord, ResolvedSlice


def record_from_generation(row):
    return AmendmentRecord(
        effective_from=row.effective_from,
        changes=deepcopy(row.changes),
        committed_revision=row.committed_revision,
        window_version=row.window_version,
    )


def order_records(records):
    return sorted(
        records,
        key=lambda item: (
            item.effective_from,
            item.committed_revision,
            item.window_version,
        ),
    )


def resolved_snapshots(records):
    slices = []
    for effective_from, group in groupby(
        order_records(records), key=lambda item: item.effective_from
    ):
        selected = list(group)[-1]
        state = validate_state(dict(selected.changes))
        slices.append(
            ResolvedSlice(
                effective_from=effective_from,
                state=state,
                committed_revision=selected.committed_revision,
                window_version=selected.window_version,
            )
        )
    return slices


def state_before(records, effective_from):
    inherited = None
    for item in resolved_snapshots(records):
        if item.effective_from <= effective_from:
            inherited = deepcopy(item.state)
    if inherited is None:
        raise ValidationError("no state exists before effective_from")
    return inherited


def candidate_snapshots(records, candidate):
    values = list(records)
    values.append(candidate)
    return resolved_snapshots(values)


def merge_records(records):
    state = {}
    slices = []
    for effective_from, group in groupby(
        order_records(records), key=lambda item: item.effective_from
    ):
        revision = 0
        version = 0
        for item in group:
            state = apply_changes(state, item.changes)
            revision = item.committed_revision
            version = item.window_version
        state = validate_state(state)
        slices.append(
            ResolvedSlice(
                effective_from=effective_from,
                state=deepcopy(state),
                committed_revision=revision,
                window_version=version,
            )
        )
    return slices


def current_slice(slices):
    if not slices:
        raise ValidationError("window has no state")
    return slices[-1]


def slice_bounds(slices):
    for index, item in enumerate(slices):
        following = slices[index + 1].effective_from if index + 1 < len(slices) else None
        yield item, following


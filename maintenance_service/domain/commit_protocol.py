from dataclasses import dataclass

from rest_framework.exceptions import ValidationError

from .types import CommitDraft, OperationKind


@dataclass(frozen=True)
class CommitShape:
    size: int
    create_ids: tuple[str, ...]
    patch_ids: tuple[str, ...]
    request_ids: tuple[str, ...]

    @property
    def lock_ids(self):
        return tuple(sorted(self.patch_ids))

    @property
    def all_ids(self):
        return tuple(sorted(self.request_ids))

    def contains(self, window_id):
        return window_id in self.request_ids

    @property
    def is_mixed(self):
        return bool(self.create_ids and self.patch_ids)


def describe_commit(draft: CommitDraft):
    request_ids = draft.window_ids
    if not 1 <= len(request_ids) <= 32:
        raise ValidationError("a commit requires between one and 32 operations")
    if len(set(request_ids)) != len(request_ids):
        raise ValidationError("a window may appear only once")
    create_ids = tuple(
        operation.window_id
        for operation in draft.operations
        if operation.kind is OperationKind.CREATE
    )
    patch_ids = tuple(
        operation.window_id
        for operation in draft.operations
        if operation.kind is OperationKind.PATCH
    )
    if len(create_ids) + len(patch_ids) != len(request_ids):
        raise ValidationError("unsupported operation type")
    return CommitShape(
        size=len(request_ids),
        create_ids=create_ids,
        patch_ids=patch_ids,
        request_ids=request_ids,
    )


def operation_positions(draft):
    return {
        operation.window_id: position
        for position, operation in enumerate(draft.operations)
    }


def same_members(left, right):
    return set(left.window_ids) == set(right.window_ids)


def single_operation(draft):
    if len(draft.operations) != 1:
        raise ValidationError("expected one operation")
    return draft.operations[0]

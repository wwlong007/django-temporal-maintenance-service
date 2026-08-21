from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Iterable, Mapping


class OperationKind(str, Enum):
    CREATE = "create"
    PATCH = "patch"


@dataclass(frozen=True)
class OperationDraft:
    kind: OperationKind
    window_id: str
    effective_from: datetime
    values: Mapping[str, Any]
    expected_version: int | None = None

    @property
    def is_create(self):
        return self.kind is OperationKind.CREATE

    @property
    def is_patch(self):
        return self.kind is OperationKind.PATCH

    def with_values(self, values):
        return OperationDraft(
            kind=self.kind,
            window_id=self.window_id,
            effective_from=self.effective_from,
            values=values,
            expected_version=self.expected_version,
        )


@dataclass(frozen=True)
class CommitDraft:
    operations: tuple[OperationDraft, ...]

    @classmethod
    def from_operations(cls, operations: Iterable[OperationDraft]):
        return cls(tuple(operations))

    @property
    def window_ids(self):
        return tuple(item.window_id for item in self.operations)

    @property
    def create_ids(self):
        return tuple(item.window_id for item in self.operations if item.is_create)

    @property
    def patch_ids(self):
        return tuple(item.window_id for item in self.operations if item.is_patch)

    def __len__(self):
        return len(self.operations)


@dataclass(frozen=True)
class AmendmentRecord:
    effective_from: datetime
    changes: Mapping[str, Any]
    committed_revision: int
    window_version: int


@dataclass(frozen=True)
class ResolvedSlice:
    effective_from: datetime
    state: Mapping[str, Any]
    committed_revision: int
    window_version: int


@dataclass(frozen=True)
class Occurrence:
    start: datetime
    end: datetime
    priority: int
    window_id: str

    def clipped(self, start, end):
        left = max(self.start, start)
        right = min(self.end, end)
        if left >= right:
            return None
        return Occurrence(left, right, self.priority, self.window_id)


@dataclass(frozen=True)
class AvailabilitySegment:
    start: datetime
    end: datetime
    source_window_id: str | None = None

    @property
    def maintenance(self):
        return self.source_window_id is not None

    def as_dict(self):
        value = {
            "start": self.start,
            "end": self.end,
            "maintenance": self.maintenance,
            "available": not self.maintenance,
        }
        if self.source_window_id is not None:
            value["source_window_id"] = self.source_window_id
        return value


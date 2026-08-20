from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class CommandOutcome:
    name: str
    succeeded: bool
    revision: int | None
    affected: int
    started_at: datetime
    completed_at: datetime
    metadata: dict

    def as_dict(self):
        return {
            "name": self.name,
            "succeeded": self.succeeded,
            "calendar_revision": self.revision,
            "affected": self.affected,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata,
        }


def success(name, revision, affected=0, **metadata):
    now = datetime.now(timezone.utc)
    return CommandOutcome(name, True, revision, affected, now, now, metadata)


def failure(name, reason, **metadata):
    now = datetime.now(timezone.utc)
    return CommandOutcome(
        name, False, None, 0, now, now, {"reason": reason, **metadata}
    )


def elapsed(outcome):
    return (outcome.completed_at - outcome.started_at).total_seconds()


def merge(outcomes):
    values = tuple(outcomes)
    return {
        "commands": len(values),
        "succeeded": sum(item.succeeded for item in values),
        "affected": sum(item.affected for item in values),
        "revisions": sorted(
            {item.revision for item in values if item.revision is not None}
        ),
    }

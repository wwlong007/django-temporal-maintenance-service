from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class RevisionTrace:
    revision: int
    started_at: datetime
    completed_at: datetime | None = None

    def finish(self):
        return RevisionTrace(self.revision, self.started_at, datetime.now(timezone.utc))

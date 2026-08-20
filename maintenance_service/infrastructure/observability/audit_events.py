from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class AuditEvent:
    name: str
    organization: str
    resource: str
    occurred_at: datetime


def calendar_changed(organization, resource):
    return AuditEvent(
        "calendar.changed", organization, resource, datetime.now(timezone.utc)
    )

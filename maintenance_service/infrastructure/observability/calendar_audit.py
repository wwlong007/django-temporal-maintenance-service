from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any
from .structured_logging import event


@dataclass(frozen=True)
class CalendarAuditRecord:
    action: str
    organization: str
    resource: str
    window_id: str | None
    revision: int | None
    version: int | None
    occurred_at: datetime
    metadata: dict[str, Any]

    def payload(self):
        value = asdict(self)
        value["occurred_at"] = self.occurred_at.isoformat()
        return value


class CalendarAuditor:
    def record(
        self,
        action,
        organization,
        resource,
        window_id=None,
        revision=None,
        version=None,
        **metadata,
    ):
        record = CalendarAuditRecord(
            action,
            organization,
            resource,
            window_id,
            revision,
            version,
            datetime.now(timezone.utc),
            metadata,
        )
        event("calendar.audit", **record.payload())
        return record

    def created(self, organization, resource, window, revision):
        return self.record(
            "window.created",
            organization,
            resource,
            window.window_id,
            revision,
            window.version,
            calendar=window.calendar,
            priority=window.priority,
        )

    def updated(self, organization, resource, window, revision, changes):
        return self.record(
            "window.updated",
            organization,
            resource,
            window.window_id,
            revision,
            window.version,
            changes=changes,
        )

    def override_added(self, organization, resource, window, revision, action):
        return self.record(
            "override.added",
            organization,
            resource,
            window.window_id,
            revision,
            window.version,
            action=action,
        )

    def rebuilt(
        self, organization, resource, revision, windows, occurrences, start, end
    ):
        return self.record(
            "projection.rebuilt",
            organization,
            resource,
            None,
            revision,
            None,
            windows=windows,
            occurrences=occurrences,
            start=start.isoformat(),
            end=end.isoformat(),
        )

    def failed(self, operation, organization, resource, reason):
        return self.record(
            "operation.failed",
            organization,
            resource,
            None,
            None,
            None,
            operation=operation,
            reason=reason,
        )


def redact(metadata):
    hidden = {"password", "secret", "token", "authorization"}
    return {
        key: ("[redacted]" if key.lower() in hidden else value)
        for key, value in metadata.items()
    }


def audit_context(organization, resource, window_id=None):
    return {"organization": organization, "resource": resource, "window_id": window_id}


def audit_revision(record):
    return record.revision if isinstance(record, CalendarAuditRecord) else None


def is_write_action(action):
    return (
        action.startswith("window.")
        or action.startswith("override.")
        or action.startswith("projection.")
    )


def record_sequence(records):
    return tuple(sorted(records, key=lambda record: record.occurred_at))


def compact_records(records):
    return [
        {
            "action": record.action,
            "revision": record.revision,
            "window_id": record.window_id,
        }
        for record in record_sequence(records)
    ]

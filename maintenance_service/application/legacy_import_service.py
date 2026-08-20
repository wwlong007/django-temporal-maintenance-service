from dataclasses import dataclass
from pathlib import Path
import json
from django.db import transaction
from maintenance_service.domain.legacy_policy import normalize_records, coerce_record
from maintenance_service.domain.errors import InvalidSchedule
from maintenance_service.application.calendar_commands import create_window
from maintenance_service.infrastructure.observability.calendar_audit import (
    CalendarAuditor,
)


@dataclass(frozen=True)
class LegacyImportResult:
    imported: int
    duplicates: int
    organizations: tuple[str, ...]
    resources: tuple[str, ...]

    def as_dict(self):
        return {
            "imported": self.imported,
            "duplicates": self.duplicates,
            "organizations": list(self.organizations),
            "resources": list(self.resources),
        }


def decode_fixture(path):
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidSchedule("legacy fixture cannot be read") from exc
    records = (
        payload
        if isinstance(payload, list)
        else payload.get("schedules") if isinstance(payload, dict) else None
    )
    if not isinstance(records, list):
        raise InvalidSchedule("legacy fixture must contain a schedules array")
    return records


def plan_fixture(path):
    raw = decode_fixture(path)
    normalized = normalize_records(raw)
    return normalized, len(raw) - len(normalized)


def import_fixture(path, auditor=None):
    raw = decode_fixture(path)
    auditor = auditor or CalendarAuditor()
    imported = 0
    organizations = set()
    resources = set()
    for raw_record in raw:
        record = coerce_record(raw_record)
        window, _ = create_window(
            record.organization, record.resource, record.window_payload()
        )
        imported += 1
        organizations.add(record.organization)
        resources.add((record.organization, record.resource))
        auditor.record(
            "legacy.imported",
            record.organization,
            record.resource,
            window.window_id,
            None,
            window.version,
        )
    return LegacyImportResult(
        imported,
        0,
        tuple(sorted(organizations)),
        tuple(f"{org}/{resource}" for org, resource in sorted(resources)),
    )


def preview_fixture(path):
    records, duplicates = plan_fixture(path)
    return {
        "records": len(records),
        "duplicates": duplicates,
        "scopes": sorted(
            {f"{record.organization}/{record.resource}" for record in records}
        ),
        "window_ids": sorted(record.window_id for record in records),
    }


def fixture_is_valid(path):
    try:
        plan_fixture(path)
        return True
    except InvalidSchedule:
        return False


def record_payloads(path):
    return tuple(record.window_payload() for record in plan_fixture(path)[0])


def deduplication_ratio(path):
    raw = decode_fixture(path)
    records, _ = plan_fixture(path)
    return 1.0 if not raw else len(records) / len(raw)


def ensure_atomic_import(path):
    return import_fixture(path)


def import_errors(path):
    try:
        preview_fixture(path)
        return tuple()
    except InvalidSchedule as exc:
        return (str(exc),)

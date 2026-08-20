import base64
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable
from django.utils.dateparse import parse_datetime
from maintenance_service.domain.errors import InvalidSchedule
from maintenance_service.domain.interval_algebra import Interval
from maintenance_service.domain.interval_set import IntervalSet, SourcedInterval
from maintenance_service.domain.availability_policy import (
    AvailabilityRange,
    validate_limit,
)

MAX_QUERY_DAYS = 366
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500


@dataclass(frozen=True)
class AvailabilityQuery:
    start: datetime
    end: datetime
    timezone: str
    cursor: str | None = None
    page_size: int = DEFAULT_PAGE_SIZE
    revision: int | None = None

    def __post_init__(self):
        if self.end <= self.start:
            raise InvalidSchedule("availability range must be positive")
        if (self.end - self.start).days > MAX_QUERY_DAYS:
            raise InvalidSchedule("availability range exceeds one year")
        if self.page_size < 1 or self.page_size > MAX_PAGE_SIZE:
            raise InvalidSchedule("page size is outside supported range")


@dataclass(frozen=True)
class CursorState:
    revision: int
    offset: int
    query_start: str
    query_end: str
    timezone: str


def parse_query(params) -> AvailabilityQuery:
    start = parse_datetime(params.get("from", ""))
    end = parse_datetime(params.get("to", ""))
    if start is None or end is None:
        raise InvalidSchedule("from and to must be ISO-8601 timestamps")
    page_size = validate_limit(params.get("limit", DEFAULT_PAGE_SIZE))
    AvailabilityRange(start, end)
    requested_revision = params.get("revision")
    if requested_revision is not None:
        try:
            requested_revision = int(requested_revision)
        except (TypeError, ValueError) as exc:
            raise InvalidSchedule("revision must be an integer") from exc
        if requested_revision < 0:
            raise InvalidSchedule("revision cannot be negative")
    return AvailabilityQuery(
        start,
        end,
        params.get("timezone", "UTC"),
        params.get("cursor"),
        page_size,
        requested_revision,
    )


def encode_cursor(state: CursorState) -> str:
    raw = json.dumps(
        {
            "revision": state.revision,
            "offset": state.offset,
            "from": state.query_start,
            "to": state.query_end,
            "timezone": state.timezone,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(value: str | None, query: AvailabilityQuery, revision: int) -> int:
    if not value:
        return 0
    try:
        padded = value + "=" * (-len(value) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        state = CursorState(
            int(payload["revision"]),
            int(payload["offset"]),
            payload["from"],
            payload["to"],
            payload["timezone"],
        )
    except Exception as exc:
        raise InvalidSchedule("cursor is invalid") from exc
    if state.revision != revision:
        raise InvalidSchedule("cursor revision is stale")
    if (
        state.query_start != query.start.isoformat()
        or state.query_end != query.end.isoformat()
    ):
        raise InvalidSchedule("cursor belongs to another query")
    if state.timezone != query.timezone:
        raise InvalidSchedule("cursor belongs to another timezone")
    if state.offset < 0:
        raise InvalidSchedule("cursor offset is invalid")
    return state.offset


def build_snapshot(rows: Iterable[tuple], query: AvailabilityQuery, revision: int):
    sourced = IntervalSet(
        SourcedInterval(Interval(start, end), priority, source, row_revision)
        for start, end, priority, source, row_revision in rows
        if row_revision == revision
    )
    maintenance = sourced.bounded(query.start, query.end).resolve_priority()
    combined = []
    for item in maintenance:
        combined.append(
            {
                "maintenance": True,
                "available": False,
                "start": item.interval.start,
                "end": item.interval.end,
                "source_window_id": item.source,
            }
        )
    for interval in maintenance.complement(query.start, query.end):
        combined.append(
            {
                "maintenance": False,
                "available": True,
                "start": interval.start,
                "end": interval.end,
            }
        )
    combined.sort(key=lambda item: (item["start"], item["maintenance"]))
    offset = decode_cursor(query.cursor, query, revision)
    page = combined[offset : offset + query.page_size]
    next_cursor = None
    if offset + query.page_size < len(combined):
        next_cursor = encode_cursor(
            CursorState(
                revision,
                offset + query.page_size,
                query.start.isoformat(),
                query.end.isoformat(),
                query.timezone,
            )
        )
    return {
        "intervals": page,
        "maintenance": [item for item in page if item["maintenance"]],
        "available": [item for item in page if item["available"]],
        "calendar_revision": revision,
        "next_cursor": next_cursor,
    }

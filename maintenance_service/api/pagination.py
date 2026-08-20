from dataclasses import dataclass
from maintenance_service.domain.cursor_codec import Cursor, encode, decode
from maintenance_service.domain.errors import InvalidSchedule


@dataclass(frozen=True)
class OffsetPage:
    items: tuple
    offset: int
    limit: int
    total: int
    cursor: str | None

    def as_dict(self):
        return {
            "items": list(self.items),
            "offset": self.offset,
            "limit": self.limit,
            "total": self.total,
            "next_cursor": self.cursor,
        }


def paginate(items, offset, limit, revision, start, end):
    values = tuple(items)
    if offset < 0:
        raise InvalidSchedule("page offset is invalid")
    page = values[offset : offset + limit]
    next_value = None
    if offset + limit < len(values):
        next_value = encode(Cursor(revision, offset + limit, start, end))
    return OffsetPage(page, offset, limit, len(values), next_value)


def cursor_offset(value, revision, start, end):
    if not value:
        return 0
    cursor = decode(value)
    if cursor.revision != revision:
        raise InvalidSchedule("cursor revision is stale")
    if cursor.start != start or cursor.end != end:
        raise InvalidSchedule("cursor does not match query bounds")
    return cursor.offset


def page_metadata(page):
    return {
        "next_cursor": page.cursor,
        "returned": len(page.items),
        "total": page.total,
    }


def empty_page(limit):
    return OffsetPage(tuple(), 0, limit, 0, None)


def has_next(page):
    return page.cursor is not None


def is_first(page):
    return page.offset == 0


def request_page(query, revision, start, end):
    return cursor_offset(query.get("cursor"), revision, start, end)


def validate_page_limit(value):
    try:
        limit = int(value)
    except (TypeError, ValueError) as exc:
        raise InvalidSchedule("limit must be an integer") from exc
    if not 1 <= limit <= 500:
        raise InvalidSchedule("limit is outside range")
    return limit

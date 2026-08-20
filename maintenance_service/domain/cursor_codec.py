import base64
import json
from dataclasses import dataclass
from .errors import InvalidSchedule


@dataclass(frozen=True)
class Cursor:
    revision: int
    offset: int
    start: str
    end: str
    timezone: str = "UTC"

    def __post_init__(self):
        if self.revision < 0 or self.offset < 0:
            raise InvalidSchedule("cursor has a negative value")

    def payload(self):
        return {
            "revision": self.revision,
            "offset": self.offset,
            "from": self.start,
            "to": self.end,
            "timezone": self.timezone,
        }


def encode(cursor: Cursor):
    raw = json.dumps(cursor.payload(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode(value):
    if not isinstance(value, str) or not value:
        raise InvalidSchedule("cursor is invalid")
    try:
        raw = base64.urlsafe_b64decode(
            (value + "=" * (-len(value) % 4)).encode("ascii")
        )
        payload = json.loads(raw)
        return Cursor(
            int(payload["revision"]),
            int(payload["offset"]),
            str(payload["from"]),
            str(payload["to"]),
            str(payload.get("timezone", "UTC")),
        )
    except Exception as exc:
        raise InvalidSchedule("cursor is invalid") from exc


def verify(value, revision, start, end, timezone="UTC"):
    cursor = decode(value)
    if cursor.revision != revision:
        raise InvalidSchedule("cursor revision is stale")
    if cursor.start != start or cursor.end != end:
        raise InvalidSchedule("cursor belongs to another query")
    if cursor.timezone != timezone:
        raise InvalidSchedule("cursor belongs to another timezone")
    return cursor.offset


def first_cursor(revision, start, end, timezone="UTC"):
    return encode(Cursor(revision, 0, start, end, timezone))


def next_cursor(revision, offset, start, end, timezone="UTC"):
    return encode(Cursor(revision, offset, start, end, timezone))


def is_cursor(value):
    try:
        decode(value)
        return True
    except InvalidSchedule:
        return False

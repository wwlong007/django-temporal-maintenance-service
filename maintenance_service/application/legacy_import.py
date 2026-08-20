from datetime import datetime
from maintenance_service.domain.errors import InvalidSchedule


def normalize_legacy_record(record):
    if not record.get("timezone"):
        raise InvalidSchedule("legacy timezone is required")
    try:
        datetime.fromisoformat(record["local_start"])
    except (KeyError, ValueError) as exc:
        raise InvalidSchedule("legacy local_start is invalid") from exc
    return {
        "window_id": record["window_id"],
        "timezone": record["timezone"],
        "local_start": record["local_start"],
        "weekday": record.get("weekday", "MO"),
    }

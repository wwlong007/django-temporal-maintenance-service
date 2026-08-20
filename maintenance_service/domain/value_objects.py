from dataclasses import dataclass


@dataclass(frozen=True)
class CalendarKey:
    organization: str
    resource: str
    window_id: str

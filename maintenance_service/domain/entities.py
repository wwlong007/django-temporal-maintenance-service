from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CalendarSpan:
    start: datetime
    end: datetime
    priority: int
    source: str

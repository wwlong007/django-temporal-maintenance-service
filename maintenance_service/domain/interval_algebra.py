from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Interval:
    start: datetime
    end: datetime

    def __post_init__(self):
        if self.end <= self.start:
            raise ValueError("interval end must be after start")

    def overlaps(self, other):
        return self.start <= other.end and other.start <= self.end

    def contains(self, value):
        return self.start <= value < self.end

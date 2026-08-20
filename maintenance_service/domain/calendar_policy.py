from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class ExpansionPolicy:
    horizon: timedelta = timedelta(days=730)
    maximum_occurrences: int = 10000
    reject_nonexistent_local_time: bool = True
    choose_late_fold: bool = True


DEFAULT_POLICY = ExpansionPolicy()

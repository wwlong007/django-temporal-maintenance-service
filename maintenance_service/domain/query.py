from dataclasses import dataclass
from datetime import timedelta, timezone

from rest_framework.exceptions import ValidationError


MAX_RANGE = timedelta(days=366)


@dataclass(frozen=True)
class AvailabilityQuery:
    start: object
    end: object
    revision: int | None = None

    @classmethod
    def from_values(cls, values):
        start = values["from"].astimezone(timezone.utc)
        end = values["to"].astimezone(timezone.utc)
        query = cls(start=start, end=end, revision=values.get("revision"))
        query.validate()
        return query

    def validate(self):
        if self.end <= self.start:
            raise ValidationError("to must be after from")
        if self.end - self.start > MAX_RANGE:
            raise ValidationError("range is too long")
        if self.revision is not None and self.revision < 0:
            raise ValidationError("revision must not be negative")
        return self

    def at_revision(self, revision):
        return AvailabilityQuery(self.start, self.end, revision)


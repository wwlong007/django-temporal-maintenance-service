from dataclasses import dataclass
from datetime import datetime
from django.db.models import Q
from maintenance_service.domain.errors import InvalidSchedule


@dataclass(frozen=True)
class RangeFilter:
    start: datetime
    end: datetime

    def __post_init__(self):
        if self.end <= self.start:
            raise InvalidSchedule("range filter must be positive")

    def overlap_q(self, start_field="start", end_field="end"):
        return Q(**{f"{start_field}__lt": self.end, f"{end_field}__gt": self.start})

    def contains_q(self, instant, start_field="start", end_field="end"):
        return Q(**{f"{start_field}__lte": instant, f"{end_field}__gt": instant})


def scope_q(organization, resource):
    return Q(window__organization=organization, window__resource=resource)


def revision_q(revision):
    return Q(revision=revision)


def active_window_q():
    return Q(window__active=True)


def ordered_range(queryset):
    return queryset.order_by("start", "end", "id")


def page_after(queryset, start=None, identifier=None):
    if start is None:
        return queryset
    if identifier is None:
        return queryset.filter(start__gt=start)
    return queryset.filter(Q(start__gt=start) | Q(start=start, id__gt=identifier))


def validate_keyset(start, identifier):
    if start is None and identifier is not None:
        raise InvalidSchedule("keyset identifier needs a start timestamp")
    if identifier is not None and int(identifier) < 0:
        raise InvalidSchedule("keyset identifier is invalid")
    return start, identifier


def range_summary(value):
    return {"from": value.start.isoformat(), "to": value.end.isoformat()}

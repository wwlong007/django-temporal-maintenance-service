from datetime import datetime, timezone, timedelta
from django.utils.dateparse import parse_datetime
from maintenance_service.models import Occurrence
from maintenance_service.domain.recurrence import expand
from maintenance_service.domain.precedence import merge_occurrences


def rebuild_window(window, revision, start=None, end=None):
    start = start or datetime.now(timezone.utc)
    end = end or start + timedelta(days=730)
    base = expand(window.rule, window.timezone, start, end)
    exceptions = window.exceptions or {}
    duration = timedelta(minutes=int(window.rule.get("duration_minutes", 60)))
    rdates = [
        (parse_datetime(x), parse_datetime(x) + duration)
        for x in exceptions.get("rdates", [])
    ]
    exdates = [parse_datetime(x) for x in exceptions.get("exdates", [])]
    overrides = list(
        window.overrides.values("original_start", "action", "start", "end")
    )
    merged = merge_occurrences(base, rdates, exdates, overrides)
    Occurrence.objects.filter(window=window).delete()
    Occurrence.objects.bulk_create(
        [
            Occurrence(
                window=window,
                start=s,
                end=e,
                span=(s, e),
                priority=window.priority,
                source=window.window_id,
                revision=revision,
            )
            for s, e in merged
        ]
    )

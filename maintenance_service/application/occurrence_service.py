from datetime import datetime, timezone, timedelta
from maintenance_service.models import Occurrence
from maintenance_service.application.generation_projection import generation_intervals


def rebuild_window(window, revision, start=None, end=None):
    start = start or datetime.now(timezone.utc)
    end = end or start + timedelta(days=730)
    merged, priority = generation_intervals(window, revision, start, end)
    Occurrence.objects.filter(window=window).delete()
    Occurrence.objects.bulk_create(
        [
            Occurrence(
                window=window,
                start=s,
                end=e,
                span=(s, e),
                priority=priority,
                source=window.window_id,
                revision=revision,
            )
            for s, e in merged
        ]
    )

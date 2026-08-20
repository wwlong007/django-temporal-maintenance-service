from maintenance_service.models import Occurrence
from maintenance_service.domain.conflicts import effective_intervals


def project_resource_conflicts(resource):
    rows = list(
        Occurrence.objects.filter(
            window__resource=resource, window__active=True
        ).values_list("start", "end", "priority", "source")
    )
    effective = effective_intervals(rows)
    return [
        {"start": span.start, "end": span.end, "priority": priority, "source": source}
        for span, priority, source in effective
    ]


def has_overlap(left, right):
    return left.start < right.end and right.start < left.end

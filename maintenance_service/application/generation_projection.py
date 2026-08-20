from datetime import timedelta

from django.utils.dateparse import parse_datetime

from maintenance_service.domain.precedence import merge_occurrences
from maintenance_service.domain.recurrence import expand


def generation_intervals(window, revision, start, end):
    generation = (
        window.generations.filter(committed_revision__lte=revision)
        .order_by("-effective_from", "-committed_revision")
        .first()
    )
    if generation is None or not generation.active:
        return [], window.priority
    base = expand(generation.rule, generation.timezone, start, end)
    duration = timedelta(minutes=int(generation.rule.get("duration_minutes", 60)))
    rdates = [
        (parse_datetime(value), parse_datetime(value) + duration)
        for value in generation.exceptions.get("rdates", [])
    ]
    exdates = [parse_datetime(value) for value in generation.exceptions.get("exdates", [])]
    overrides = list(
        window.overrides.filter(committed_revision__lte=revision).values(
            "original_start", "action", "start", "end"
        )
    )
    return merge_occurrences(base, rdates, exdates, overrides), generation.priority

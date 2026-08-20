from dataclasses import dataclass
from datetime import datetime
from typing import Iterable
from maintenance_service.domain.recurrence_limits import validate_expansion_range
from maintenance_service.domain.schedule_diff import ScheduleDiff
from maintenance_service.domain.errors import InvalidSchedule


@dataclass(frozen=True)
class RebuildTarget:
    window_id: str
    version: int
    active: bool
    estimated_occurrences: int


@dataclass(frozen=True)
class RebuildPlan:
    organization: str
    resource: str
    start: datetime
    end: datetime
    revision: int
    targets: tuple[RebuildTarget, ...]
    reason: str

    def __post_init__(self):
        validate_expansion_range(self.start, self.end)
        if self.revision < 0:
            raise InvalidSchedule("rebuild revision is invalid")

    @property
    def active_targets(self):
        return tuple(target for target in self.targets if target.active)

    @property
    def total_estimate(self):
        return sum(target.estimated_occurrences for target in self.active_targets)

    def as_dict(self):
        return {
            "organization": self.organization,
            "resource": self.resource,
            "from": self.start,
            "to": self.end,
            "revision": self.revision,
            "reason": self.reason,
            "targets": [target.__dict__ for target in self.targets],
        }


def estimate_window(window, start, end):
    rule = window.rule
    interval = max(1, int(rule.get("interval", 1)))
    if rule.get("frequency") == "weekly":
        weeks = max(1, ((end - start).days // 7) + 1)
        estimate = ((weeks + interval - 1) // interval) * max(
            1, len(rule.get("weekdays", []))
        )
    else:
        months = max(1, ((end.year - start.year) * 12) + end.month - start.month + 1)
        estimate = (months + interval - 1) // interval
    if rule.get("count") is not None:
        estimate = min(estimate, int(rule["count"]))
    return estimate


def build_plan(organization, resource, windows, start, end, revision, reason):
    targets = tuple(
        RebuildTarget(
            window.window_id,
            window.version,
            window.active,
            estimate_window(window, start, end),
        )
        for window in windows
    )
    plan = RebuildPlan(organization, resource, start, end, revision, targets, reason)
    if plan.total_estimate > 10_000:
        raise InvalidSchedule("rebuild would exceed the occurrence limit")
    return plan


def plan_for_change(
    organization, resource, window, start, end, revision, diff: ScheduleDiff
):
    reason = "rule-change" if diff.needs_rebuild else "metadata-change"
    windows = (window,) if diff.needs_rebuild else tuple()
    return build_plan(organization, resource, windows, start, end, revision, reason)


def can_reuse_projection(plan):
    return plan.reason == "metadata-change" or not plan.targets


def validate_plan_against_windows(plan, windows):
    expected = {(target.window_id, target.version) for target in plan.targets}
    actual = {(window.window_id, window.version) for window in windows}
    return expected == actual


def affected_window_ids(plan):
    return tuple(target.window_id for target in plan.active_targets)


def split_plan(plan, maximum_targets=100):
    if maximum_targets < 1:
        raise InvalidSchedule("maximum targets must be positive")
    targets = plan.targets
    return tuple(
        RebuildPlan(
            plan.organization,
            plan.resource,
            plan.start,
            plan.end,
            plan.revision,
            targets[index : index + maximum_targets],
            plan.reason,
        )
        for index in range(0, len(targets), maximum_targets)
    )


def describe_plan(plan):
    return f"{plan.organization}/{plan.resource} revision={plan.revision} targets={len(plan.active_targets)} estimate={plan.total_estimate}"

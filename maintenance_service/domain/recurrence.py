from datetime import timedelta
from dateutil.rrule import rrule, WEEKLY, MONTHLY, MO, TU, WE, TH, FR, SA, SU
from .timezone_policy import resolve_local, as_utc
from .errors import InvalidSchedule
from .rule_validation import validate_rule
from .recurrence_limits import preflight, enforce_limit

WEEKDAYS = {"MO": MO, "TU": TU, "WE": WE, "TH": TH, "FR": FR, "SA": SA, "SU": SU}


def expand(rule, timezone_name, start, end):
    rule = validate_rule(rule).as_dict()
    preflight(rule, start, end)
    freq_name = rule.get("frequency", "weekly").lower()
    freq = (
        WEEKLY if freq_name == "weekly" else MONTHLY if freq_name == "monthly" else None
    )
    if freq is None:
        raise InvalidSchedule("frequency must be weekly or monthly")
    local_start = resolve_local(rule["start"], timezone_name)
    duration = timedelta(minutes=int(rule["duration_minutes"]))
    kwargs = {
        "freq": freq,
        "dtstart": local_start,
        "interval": int(rule.get("interval", 1)),
    }
    if rule.get("count") is not None:
        kwargs["count"] = int(rule["count"])
    if rule.get("until"):
        kwargs["until"] = resolve_local(rule["until"], timezone_name)
    if freq == WEEKLY:
        days = tuple(WEEKDAYS[d] for d in rule.get("weekdays", []))
        if days:
            kwargs["byweekday"] = days
    lower = start.astimezone(local_start.tzinfo)
    upper = end.astimezone(local_start.tzinfo)
    occurrences = rrule(**kwargs).between(lower, upper, inc=True)
    return enforce_limit(
        ((as_utc(item), as_utc(item + duration)) for item in occurrences),
        preflight(rule, start, end),
    )

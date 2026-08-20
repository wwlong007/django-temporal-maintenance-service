from maintenance_service.domain.recurrence import expand


class RecurrenceAdapter:
    def occurrences(self, rule, timezone_name, start, end):
        return expand(rule, timezone_name, start, end)

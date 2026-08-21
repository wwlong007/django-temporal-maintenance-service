from dataclasses import dataclass

from rest_framework.exceptions import ValidationError

from maintenance_service.domain.calendar import compose_availability
from maintenance_service.repositories.catalog import open_catalog


@dataclass(frozen=True)
class AvailabilitySnapshot:
    revision: int
    intervals: tuple


class AvailabilityReadModel:
    def __init__(self, organization_key, resource_key):
        self.catalog = open_catalog(organization_key, resource_key)

    def revision(self, requested):
        value = self.catalog.current_revision if requested is None else requested
        if not self.catalog.has_revision(value):
            raise ValidationError("revision is not available")
        return value

    def snapshot(self, start, end, requested_revision=None):
        revision = self.revision(requested_revision)
        histories = self.catalog.histories(revision)
        intervals = compose_availability(histories, start, end)
        return AvailabilitySnapshot(revision, tuple(intervals))


def read_availability(organization_key, resource_key, query):
    model = AvailabilityReadModel(organization_key, resource_key)
    return model.snapshot(query.start, query.end, query.revision)


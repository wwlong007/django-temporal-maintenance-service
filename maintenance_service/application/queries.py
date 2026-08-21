from maintenance_service.domain.query import AvailabilityQuery

from .read_models import read_availability
from .responses import availability_result


class AvailabilityService:
    def __init__(self, organization_key, resource_key):
        self.organization_key = organization_key
        self.resource_key = resource_key

    def execute(self, values):
        query = AvailabilityQuery.from_values(values)
        snapshot = read_availability(
            self.organization_key, self.resource_key, query
        )
        return availability_result(snapshot.revision, snapshot.intervals)


def availability(organization_key, resource_key, query):
    return AvailabilityService(organization_key, resource_key).execute(query)

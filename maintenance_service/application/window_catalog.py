from dataclasses import dataclass
from maintenance_service.infrastructure.persistence.calendar_repository import (
    CalendarRepository,
)
from maintenance_service.domain.errors import NotFound


@dataclass(frozen=True)
class WindowCatalogItem:
    window_id: str
    calendar: str
    priority: int
    version: int
    active: bool
    timezone: str

    def as_dict(self):
        return self.__dict__


class WindowCatalog:
    def __init__(self, repository=None):
        self.repository = repository or CalendarRepository()

    def list(self, organization, resource, active=None):
        scope = self.repository.find_scope(organization, resource)
        return tuple(
            WindowCatalogItem(
                item.window_id,
                item.calendar,
                item.priority,
                item.version,
                item.active,
                item.timezone,
            )
            for item in self.repository.list_windows(scope, active)
        )

    def get(self, organization, resource, window_id):
        scope = self.repository.find_scope(organization, resource)
        item = self.repository.window(scope, window_id)
        return WindowCatalogItem(
            item.window_id,
            item.calendar,
            item.priority,
            item.version,
            item.active,
            item.timezone,
        )

    def ids(self, organization, resource):
        return tuple(item.window_id for item in self.list(organization, resource))

    def active_ids(self, organization, resource):
        return tuple(item.window_id for item in self.list(organization, resource, True))

    def calendars(self, organization, resource):
        return tuple(
            sorted({item.calendar for item in self.list(organization, resource)})
        )

    def priorities(self, organization, resource):
        return {
            item.window_id: item.priority for item in self.list(organization, resource)
        }

    def find_by_calendar(self, organization, resource, calendar):
        return tuple(
            item
            for item in self.list(organization, resource)
            if item.calendar == calendar
        )

    def exists(self, organization, resource, window_id):
        try:
            self.get(organization, resource, window_id)
            return True
        except NotFound:
            return False

    def summary(self, organization, resource):
        values = self.list(organization, resource)
        return {
            "total": len(values),
            "active": sum(item.active for item in values),
            "calendars": self.calendars(organization, resource),
            "window_ids": tuple(item.window_id for item in values),
        }

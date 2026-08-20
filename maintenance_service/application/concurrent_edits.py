from dataclasses import dataclass
from django.db import transaction, OperationalError
from maintenance_service.domain.errors import VersionConflict
from maintenance_service.domain.revision_policy import require_version
from maintenance_service.infrastructure.persistence.calendar_repository import (
    CalendarRepository,
)


@dataclass(frozen=True)
class EditOutcome:
    committed: bool
    version: int | None
    revision: int | None
    conflict: bool = False

    def as_dict(self):
        return self.__dict__


class ConcurrentEditCoordinator:
    def __init__(self, repository=None):
        self.repository = repository or CalendarRepository()

    @transaction.atomic
    def apply(self, organization, resource, window_id, expected_version, changes):
        scope = self.repository.get_or_create_scope(organization, resource)
        window = self.repository.window(scope, window_id, lock=True)
        require_version(expected_version, window.version)
        for name, value in changes.items():
            setattr(window, name, value)
        window.version += 1
        window.save()
        revision = self.repository.increment_revision(scope)
        return EditOutcome(True, window.version, revision.value)

    def attempt(self, *args, **kwargs):
        try:
            return self.apply(*args, **kwargs)
        except VersionConflict:
            return EditOutcome(False, None, None, True)

    def retryable(self, attempts, operation):
        last = None
        for _ in range(attempts):
            try:
                return operation()
            except OperationalError as exc:
                last = exc
        if last:
            raise last
        return None

    def compare(self, organization, resource, window_id, expected_version):
        scope = self.repository.find_scope(organization, resource)
        window = self.repository.window(scope, window_id)
        return window.version == expected_version

    def current(self, organization, resource, window_id):
        scope = self.repository.find_scope(organization, resource)
        window = self.repository.window(scope, window_id)
        revision = self.repository.revision(scope)
        return EditOutcome(True, window.version, revision.value)

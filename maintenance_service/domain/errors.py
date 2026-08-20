class DomainError(Exception):
    status_code = 400


class VersionConflict(DomainError):
    status_code = 409


class InvalidSchedule(DomainError):
    status_code = 422


class NotFound(DomainError):
    status_code = 404

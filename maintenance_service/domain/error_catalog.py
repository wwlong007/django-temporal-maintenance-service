from dataclasses import dataclass
from .errors import DomainError, InvalidSchedule, VersionConflict, NotFound


@dataclass(frozen=True)
class ErrorDescriptor:
    code: str
    status: int
    retryable: bool = False


INVALID_SCHEDULE = ErrorDescriptor("invalid_schedule", 422)
VERSION_CONFLICT = ErrorDescriptor("version_conflict", 409, True)
MISSING_RESOURCE = ErrorDescriptor("not_found", 404)
UNEXPECTED = ErrorDescriptor("internal_error", 500, True)


def descriptor(error):
    if isinstance(error, VersionConflict):
        return VERSION_CONFLICT
    if isinstance(error, NotFound):
        return MISSING_RESOURCE
    if isinstance(error, InvalidSchedule):
        return INVALID_SCHEDULE
    return UNEXPECTED


def error_payload(error):
    value = descriptor(error)
    return {"code": value.code, "detail": str(error), "retryable": value.retryable}


def is_client_error(error):
    return descriptor(error).status < 500


def is_retryable(error):
    return descriptor(error).retryable


def status(error):
    return descriptor(error).status


def wrap(error):
    if isinstance(error, DomainError):
        return error
    return InvalidSchedule(str(error))


def response_tuple(error):
    value = descriptor(error)
    return error_payload(error), value.status

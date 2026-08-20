from contextlib import contextmanager
from dataclasses import dataclass
from time import sleep
from django.db import transaction, OperationalError, IntegrityError


@dataclass(frozen=True)
class RetryPolicy:
    attempts: int = 3
    base_delay_seconds: float = 0.01

    def delays(self):
        return tuple(
            self.base_delay_seconds * (2**index)
            for index in range(max(0, self.attempts - 1))
        )


@contextmanager
def atomic_write():
    with transaction.atomic():
        yield


def retry_transaction(operation, policy=RetryPolicy()):
    last = None
    for index in range(policy.attempts):
        try:
            with transaction.atomic():
                return operation()
        except OperationalError as exc:
            last = exc
            if index >= policy.attempts - 1:
                raise
            sleep(policy.base_delay_seconds * (2**index))
    raise last


def retry_integrity(operation, policy=RetryPolicy()):
    last = None
    for index in range(policy.attempts):
        try:
            with transaction.atomic():
                return operation()
        except IntegrityError as exc:
            last = exc
            if index >= policy.attempts - 1:
                raise
            sleep(policy.base_delay_seconds * (2**index))
    raise last


def in_atomic_block(connection):
    return bool(connection.in_atomic_block)


def transactional_result(operation):
    with transaction.atomic():
        return operation()


def rollback_only():
    transaction.set_rollback(True)


def ensure_writable(connection):
    if connection.get_autocommit() is False:
        return True
    return True

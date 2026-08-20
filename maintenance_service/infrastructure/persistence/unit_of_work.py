from contextlib import contextmanager
from django.db import transaction


@contextmanager
def calendar_unit_of_work():
    with transaction.atomic():
        yield

from django.db import transaction
from maintenance_service.models import MaintenanceWindow
from maintenance_service.domain.errors import VersionConflict


def lock_window(organization, resource, window_id):
    return MaintenanceWindow.objects.select_for_update().get(
        organization=organization, resource=resource, window_id=window_id
    )


@transaction.atomic
def compare_and_update(window, expected_version, **changes):
    if window.version != expected_version:
        raise VersionConflict("version conflict")
    for key, value in changes.items():
        setattr(window, key, value)
    window.version += 1
    window.save()
    return window

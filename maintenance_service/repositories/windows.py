from django.http import Http404

from maintenance_service.api.errors import Conflict
from maintenance_service.models import MaintenanceWindow


def scope_windows(scope):
    return MaintenanceWindow.objects.filter(
        organization=scope.organization,
        resource=scope.resource,
    ).order_by("window_id")


def find_window(scope, window_id):
    return scope_windows(scope).filter(window_id=window_id).first()


def require_window(scope, window_id):
    window = find_window(scope, window_id)
    if window is None:
        raise Http404
    return window


def require_version(window, expected_version):
    if window.version != expected_version:
        raise Conflict()
    return window


def ensure_available(scope, window_id):
    if scope_windows(scope).filter(window_id=window_id).exists():
        raise Conflict("window already exists")


def create_window(scope, operation, state):
    ensure_available(scope, operation.window_id)
    return MaintenanceWindow.objects.create(
        organization=scope.organization,
        resource=scope.resource,
        window_id=operation.window_id,
        effective_from=operation.effective_from,
        timezone=state["timezone"],
        rule=state["rule"],
        priority=state["priority"],
        active=state["active"],
        version=1,
    )


def windows_by_ids(scope, window_ids):
    return {
        row.window_id: row
        for row in scope_windows(scope).filter(window_id__in=window_ids)
    }


def require_windows(scope, window_ids):
    rows = windows_by_ids(scope, window_ids)
    if len(rows) != len(set(window_ids)):
        raise Http404
    return rows


def lock_windows(scope, window_ids):
    rows = (
        MaintenanceWindow.objects.select_for_update()
        .filter(
            organization=scope.organization,
            resource=scope.resource,
            window_id__in=window_ids,
        )
        .order_by("window_id")
    )
    values = {row.window_id: row for row in rows}
    if len(values) != len(set(window_ids)):
        raise Http404
    return values


def created_by_revision(scope, revision):
    return scope_windows(scope).filter(generations__committed_revision__lte=revision).distinct()


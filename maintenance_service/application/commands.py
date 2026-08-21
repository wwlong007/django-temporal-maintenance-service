from maintenance_service.domain.operations import normalize_create, normalize_patch

from .coordinator import coordinator


def create_window(organization_key, resource_key, data):
    draft = normalize_create(data)
    return coordinator(organization_key, resource_key).commit_one(draft)


def patch_window(organization_key, resource_key, window_id, data):
    draft = normalize_patch(window_id, data)
    return coordinator(organization_key, resource_key).commit_one(draft)


def submit_operation(organization_key, resource_key, operation):
    if operation["type"] == "create":
        return create_window(organization_key, resource_key, operation)
    values = {key: value for key, value in operation.items() if key not in {"type", "window_id"}}
    return patch_window(
        organization_key,
        resource_key,
        operation["window_id"],
        values,
    )

from maintenance_service.application.commands import create_window, patch_window


def commit_batch(organization_key, resource_key, operations):
    results = []
    for operation in operations:
        values = dict(operation)
        operation_type = values.pop("type")
        window_id = values.pop("window_id")
        if operation_type == "create":
            values["window_id"] = window_id
            result = create_window(organization_key, resource_key, values)
        else:
            result = patch_window(
                organization_key, resource_key, window_id, values
            )
        results.append(result)
    return {
        "calendar_revision": results[-1]["calendar_revision"],
        "results": results,
    }

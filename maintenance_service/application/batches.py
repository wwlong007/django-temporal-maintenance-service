from maintenance_service.domain.operations import normalize_batch

from .coordinator import coordinator


def commit_batch(organization_key, resource_key, operations):
    draft = normalize_batch(operations)
    return coordinator(organization_key, resource_key).commit_many(draft)


def batch_window_ids(operations):
    return tuple(operation["window_id"] for operation in operations)


def batch_size(operations):
    return len(operations)

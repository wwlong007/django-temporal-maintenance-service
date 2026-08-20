from .errors import InvalidSchedule


def normalize_key(value, name):
    if not isinstance(value, str) or not value.strip():
        raise InvalidSchedule(f"{name} is required")
    result = value.strip()
    if len(result) > 100:
        raise InvalidSchedule(f"{name} is too long")
    return result


def scope(organization, resource):
    return normalize_key(organization, "organization"), normalize_key(
        resource, "resource"
    )


def same_scope(left, right):
    return scope(*left) == scope(*right)


def scope_label(organization, resource):
    return "/".join(scope(organization, resource))


def scope_parts(label):
    organization, separator, resource = label.partition("/")
    if not separator:
        raise InvalidSchedule("scope label is invalid")
    return scope(organization, resource)


def scoped_id(organization, resource, value):
    return f"{scope_label(organization,resource)}:{value}"


def is_scoped(value):
    return "/" in value and ":" in value


SCOPE_SEPARATOR = "/"

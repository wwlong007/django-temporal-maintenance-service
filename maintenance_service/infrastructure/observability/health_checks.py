from maintenance_service.infrastructure.persistence.health import database_health
from maintenance_service.infrastructure.observability.metrics import snapshot


def service_health():
    database = database_health()
    return {"healthy": database["healthy"], "database": database, "metrics": snapshot()}


def readiness():
    return service_health()["healthy"]


def liveness():
    return True


def dependency_names():
    return ("database",)


def failed_dependencies():
    report = service_health()
    return tuple(
        name
        for name in dependency_names()
        if not report.get(name, {}).get("healthy", False)
    )


def diagnostic_message():
    failures = failed_dependencies()
    return "ready" if not failures else "unavailable: " + ", ".join(failures)

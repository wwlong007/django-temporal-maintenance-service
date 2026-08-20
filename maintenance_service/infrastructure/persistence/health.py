from django.db import connection


def database_health():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return {"healthy": True, "vendor": connection.vendor}
    except Exception as exc:
        return {
            "healthy": False,
            "vendor": connection.vendor,
            "reason": type(exc).__name__,
        }

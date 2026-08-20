from django.db import connection


def database_capabilities():
    return {
        "vendor": connection.vendor,
        "supports_transactions": connection.features.supports_transactions,
        "supports_select_for_update": connection.features.has_select_for_update,
    }

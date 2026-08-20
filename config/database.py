from contextlib import contextmanager
from django.db import connection


def database_vendor():
    return connection.vendor


def database_version():
    with connection.cursor() as cursor:
        cursor.execute("SHOW server_version")
        return cursor.fetchone()[0]


def postgres_extensions():
    if connection.vendor != "postgresql":
        return tuple()
    with connection.cursor() as cursor:
        cursor.execute("SELECT extname FROM pg_extension ORDER BY extname")
        return tuple(row[0] for row in cursor.fetchall())


def has_extension(name):
    return name in postgres_extensions()


def range_support_available():
    return connection.vendor == "postgresql" and has_extension("btree_gist")


def connection_details():
    return {
        "vendor": connection.vendor,
        "alias": connection.alias,
        "in_atomic_block": connection.in_atomic_block,
    }


@contextmanager
def cursor():
    with connection.cursor() as value:
        yield value


def ping():
    with connection.cursor() as value:
        value.execute("SELECT 1")
        return value.fetchone()[0] == 1


def explain(query, params=None):
    with connection.cursor() as value:
        value.execute("EXPLAIN " + query, params or [])
        return tuple(row[0] for row in value.fetchall())

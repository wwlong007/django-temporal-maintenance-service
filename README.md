# Temporal Maintenance Service

This Django service manages maintenance calendars for organization-scoped resources. It stores local-time rules with IANA time zones, expands recurring windows, applies date exceptions and exposes a revisioned availability view.

## Development

Create a PostgreSQL database, install the project with `pip install -e .`, then run `python manage.py migrate` and `python manage.py runserver`. The API is rooted at `/api/v1/`.

## Operations

`python manage.py rebuild_occurrences --organization ORG --resource RESOURCE --from START --to END` rebuilds the materialized occurrence view for a resource. Timestamps in the API are ISO-8601 values and returned intervals use UTC.

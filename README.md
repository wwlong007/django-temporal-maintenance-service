# Temporal Maintenance Service

This Django service manages maintenance calendars for organization-scoped resources. It stores local-time rules with IANA time zones, expands recurring windows, applies date exceptions and exposes revisioned availability views.

Window writes carry an `effective_from` instant. A resource calendar can therefore contain committed rule generations that take effect in the future or revise an earlier part of the schedule. Availability may be read at a committed `revision`; cursors retain that revision so long-running consumers can finish one stable snapshot while newer calendar edits are committed.

Organizations may also define effective-dated maintenance policies over groups of resources and their fault zones. A maintenance plan applies window changes across one or more resources as a single organization revision. The maintenance-impact endpoint reports the resources and zones affected by each interval and supports historical revision reads for operational review.

## Development

Create a PostgreSQL database, install the project with `pip install -e .`, then run `python manage.py migrate` and `python manage.py runserver`. The API is rooted at `/api/v1/`.

## Operations

`python manage.py rebuild_occurrences --organization ORG --resource RESOURCE --from START --to END [--revision REVISION]` rebuilds the materialized occurrence view for a resource snapshot. Timestamps in the API are ISO-8601 values and returned intervals use UTC.

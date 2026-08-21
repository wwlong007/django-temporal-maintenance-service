# Temporal Maintenance Service

This Django service stores IANA-time-zone weekly maintenance rules for organization-scoped resources. Window changes have an effective time and a resource calendar revision, allowing availability to be read at a previously committed revision. A batch endpoint accepts several same-scope window operations as one requested calendar change.

The API exposes maintenance-window creation, patching, batch submission, and availability reads under `/api/v1/organizations/{organization}/resources/{resource}/`.

## Development

Create a PostgreSQL database, install the project with `pip install -e .`, then run `python manage.py migrate` and `python manage.py runserver`. Timestamps in availability responses use UTC.

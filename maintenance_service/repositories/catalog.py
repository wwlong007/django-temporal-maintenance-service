from dataclasses import dataclass

from .commits import commit_at, is_complete, visible_commits
from .history import load_scope_history
from .scopes import find_scope


@dataclass(frozen=True)
class CalendarCatalog:
    organization_key: str
    resource_key: str
    scope: object | None

    @classmethod
    def open(cls, organization_key, resource_key):
        return cls(
            organization_key=organization_key,
            resource_key=resource_key,
            scope=find_scope(organization_key, resource_key),
        )

    @property
    def current_revision(self):
        return self.scope.current_revision if self.scope else 0

    def has_revision(self, revision):
        return 0 <= revision <= self.current_revision

    def commit(self, revision):
        if self.scope is None or revision == 0:
            return None
        return commit_at(self.scope, revision)

    def commit_is_complete(self, revision):
        commit = self.commit(revision)
        return commit is not None and is_complete(commit)

    def commits_through(self, revision):
        if self.scope is None:
            return []
        return list(visible_commits(self.scope, revision))

    def histories(self, revision):
        if self.scope is None:
            return []
        return load_scope_history(self.scope, revision)

    def revision_values(self):
        if self.scope is None:
            return []
        return list(
            visible_commits(self.scope, self.current_revision).values_list(
                "revision", flat=True
            )
        )


def open_catalog(organization_key, resource_key):
    return CalendarCatalog.open(organization_key, resource_key)


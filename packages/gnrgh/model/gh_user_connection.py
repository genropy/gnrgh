# encoding: utf-8
import re

# Pattern for role topics: sw-role-{role}-{username}
# Note: This is a workaround using repository topics to store user roles.
# Not the intended use of topics, but allows quick import of role assignments.
SW_ROLE_PATTERN = re.compile(r'^sw-role-([^-]+)-(.+)$')


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('gh_user_connection', pkey='id',
                        name_long='!![en]GitHub User Connection',
                        name_plural='!![en]GitHub User Connections')
        self.sysFields(tbl)

        # GitHub user (always required)
        tbl.column('gh_user_id', size='22', group='_',
                   name_long='!![en]GitHub User').relation(
            'gh_user.id', relation_name='connections',
            mode='foreignkey', onDelete='cascade')

        # Repository role (linked to repo_role table)
        # Only meaningful for repository connections (collaborators)
        tbl.column('repo_role_code', size=':32', group='_',
                   name_long='!![en]Repository Role', nullable=True).relation(
            'repo_role.code', relation_name='user_connections',
            mode='foreignkey', onDelete='raise')

        # Organization membership role (owner or member)
        # Only meaningful for organization connections
        tbl.column('membership', size=':10', group='_',
                   name_long='!![en]Membership', nullable=True,
                   values='owner:Owner,member:Member')

        # Connection type calculated from which FK is set
        tbl.formulaColumn('connection_type', """
            CASE
                WHEN $issue_id IS NOT NULL THEN 'issue'
                WHEN $pull_request_id IS NOT NULL THEN 'pull_request'
                WHEN $organization_id IS NOT NULL THEN 'organization'
                WHEN $repository_id IS NOT NULL THEN 'repository'
            END
        """, name_long='!![en]Connection Type')

        # Mutually exclusive foreign keys - only one should be set
        tbl.column('issue_id', size='22', group='_',
                   name_long='!![en]Issue').relation(
            'issue.id', relation_name='user_connections',
            mode='foreignkey', onDelete='cascade')

        tbl.column('pull_request_id', size='22', group='_',
                   name_long='!![en]Pull Request').relation(
            'pull_request.id', relation_name='user_connections',
            mode='foreignkey', onDelete='cascade')

        tbl.column('organization_id', size='22', group='_',
                   name_long='!![en]Organization').relation(
            'organization.id', relation_name='user_connections',
            mode='foreignkey', onDelete='cascade')

        tbl.column('repository_id', size='22', group='_',
                   name_long='!![en]Repository').relation(
            'repository.id', relation_name='user_connections',
            mode='foreignkey', onDelete='cascade')

        # Subtables for different connection types
        tbl.subtable('gh_issue_assignee', condition='$issue_id IS NOT NULL')
        tbl.subtable('gh_pr_assignee', condition='$pull_request_id IS NOT NULL')
        tbl.subtable('gh_org_member', condition='$organization_id IS NOT NULL')
        tbl.subtable('gh_repo_collaborator', condition='$repository_id IS NOT NULL')

    def addConnection(self, gh_user_id, repo_role_code=None, membership=None,
                      issue_id=None, pull_request_id=None,
                      organization_id=None, repository_id=None):
        """Add a connection between a GitHub user and an entity.

        Args:
            gh_user_id: pkey of the gh_user
            repo_role_code: repository role code (only for repository connections)
            membership: organization membership role (only for organization connections)
            issue_id, pull_request_id, organization_id, repository_id:
                mutually exclusive - only one should be set
        """
        if not gh_user_id:
            return None
        if repo_role_code:
            repo_role_code = repo_role_code.upper()
        # Build the record
        record = dict(
            gh_user_id=gh_user_id,
            repo_role_code=repo_role_code,
            membership=membership,
            issue_id=issue_id,
            pull_request_id=pull_request_id,
            organization_id=organization_id,
            repository_id=repository_id
        )

        # Check if connection already exists
        where_parts = ['$gh_user_id=:gh_user_id']
        params = dict(gh_user_id=gh_user_id)

        # Handle NULL repo_role_code in query
        if repo_role_code:
            where_parts.append('$repo_role_code=:repo_role_code')
            params['repo_role_code'] = repo_role_code
        else:
            where_parts.append('$repo_role_code IS NULL')

        if issue_id:
            where_parts.append('$issue_id=:issue_id')
            params['issue_id'] = issue_id
        elif pull_request_id:
            where_parts.append('$pull_request_id=:pull_request_id')
            params['pull_request_id'] = pull_request_id
        elif organization_id:
            where_parts.append('$organization_id=:organization_id')
            params['organization_id'] = organization_id
        elif repository_id:
            where_parts.append('$repository_id=:repository_id')
            params['repository_id'] = repository_id

        existing = self.query(
            columns='$id',
            where=' AND '.join(where_parts),
            **params
        ).fetch()

        if existing:
            return existing[0]['id']

        return self.insert(record)

    def syncAssignees(self, assignees_data, user_tbl,
                      issue_id=None, pull_request_id=None):
        """Sync assignees for an issue or pull request.

        Args:
            assignees_data: list of user dicts from GitHub API
            user_tbl: github_user table reference
            issue_id or pull_request_id: the entity to sync assignees for
        """
        # Determine which entity we're syncing
        if issue_id:
            entity_field = 'issue_id'
            entity_id = issue_id
        elif pull_request_id:
            entity_field = 'pull_request_id'
            entity_id = pull_request_id
        else:
            return

        # Delete existing assignee connections for this entity (repo_role_code is NULL for assignees)
        self.deleteSelection(
            where=f'${entity_field}=:entity_id',
            entity_id=entity_id
        )

        # Add new assignee connections (without repo_role_code)
        for assignee_data in assignees_data:
            user_pkey = user_tbl.importUser(assignee_data)
            if user_pkey:
                self.addConnection(
                    gh_user_id=user_pkey,
                    **{entity_field: entity_id}
                )

    def syncMembers(self, github_service, user_tbl, organization_id, login):
        """Sync members for an organization from GitHub API.

        Fetches owners (admin role) and members separately to properly set membership.

        Args:
            github_service: GitHub service instance
            user_tbl: gh_user table reference
            organization_id: the organization pkey
            login: organization login name for API calls
        """
        # Delete all existing member connections for this org
        self.deleteSelection(
            where='$organization_id=:organization_id',
            organization_id=organization_id
        )

        # Sync owners (admin role in API = owner membership)
        owners = github_service.getOrgMembers(organization=login, role='admin')
        for member_data in owners:
            user_pkey = user_tbl.importUser(member_data)
            if user_pkey:
                self.addConnection(
                    gh_user_id=user_pkey,
                    organization_id=organization_id,
                    membership='owner'
                )

        # Sync members
        members = github_service.getOrgMembers(organization=login, role='member')
        for member_data in members:
            user_pkey = user_tbl.importUser(member_data)
            if user_pkey:
                self.addConnection(
                    gh_user_id=user_pkey,
                    organization_id=organization_id,
                    membership='member'
                )

    def syncCollaborators(self, collaborators_data, user_tbl, repository_id, repo_role_code):
        """Sync collaborators for a repository.

        Args:
            collaborators_data: list of user dicts from GitHub API
            user_tbl: gh_user table reference
            repository_id: the repository pkey
            repo_role_code: the role code to assign
        """
        # Delete existing collaborator connections for this repo with this role
        self.deleteSelection(
            where='$repository_id=:repository_id AND $repo_role_code=:repo_role_code',
            repository_id=repository_id,
            repo_role_code=repo_role_code
        )

        # Add new collaborator connections
        for collab_data in collaborators_data:
            user_pkey = user_tbl.importUser(collab_data)
            if user_pkey:
                self.addConnection(
                    gh_user_id=user_pkey,
                    repo_role_code=repo_role_code,
                    repository_id=repository_id
                )

    def getRoleTopics(self, repository_id):
        """Get role assignments from sw-role topics for a repository.

        Parses topics matching pattern 'sw-role-{role}-{username}' and returns
        a list of (repo_role_code, username) tuples. Auto-creates repo_role
        records via sysRecord if they don't exist.

        Args:
            repository_id: The repository pkey

        Returns:
            List of tuples (repo_role_code, username) parsed from sw-role topics
        """
        topic_link_tbl = self.db.table('gnrgh.gh_topic_link')
        repo_role_tbl = self.db.table('gnrgh.repo_role')

        # Get topics from local DB
        topics = topic_link_tbl.query(
            columns='$topic_name',
            where='$repository_id=:repository_id',
            repository_id=repository_id
        ).fetch()

        role_assignments = []
        for row in topics:
            match = SW_ROLE_PATTERN.match(row['topic_name'])
            if match:
                username = match.group(1)
                topic_role = match.group(2)
                # Try to get repo_role via sysRecord, fallback to CONTRIBUTOR if not found
                syscode = topic_role.upper()
                if hasattr(repo_role_tbl, f'sysRecord_{syscode}'):
                    repo_role_code = repo_role_tbl.sysRecord(syscode)['code']
                else:
                    repo_role_code = repo_role_tbl.sysRecord('CONTRIBUTOR')['code']
                role_assignments.append((repo_role_code, username))

        return role_assignments

    def syncMembersFromTopics(self, repository_id):
        """Sync repository members from sw-role topics.

        Uses getRoleTopics to parse sw-role-{role}-{username} topics and creates
        user connections with the corresponding role.

        Args:
            repository_id: The repository pkey
        """
        user_tbl = self.db.table('gnrgh.gh_user')

        # Get role assignments from topics
        role_assignments = self.getRoleTopics(repository_id)

        # Delete existing connections for this repository
        self.deleteSelection(
            where='$repository_id=:repository_id',
            repository_id=repository_id
        )

        # Create connections from role assignments
        for repo_role_code, username in role_assignments:
            # Find user by login
            user_rows = user_tbl.query(
                columns='$id',
                where='$login=:login',
                login=username
            ).fetch()

            if not user_rows:
                # User not found, skip
                continue

            gh_user_id = user_rows[0]['id']

            # Add user connection
            self.addConnection(
                gh_user_id=gh_user_id,
                repo_role_code=repo_role_code,
                repository_id=repository_id
            )

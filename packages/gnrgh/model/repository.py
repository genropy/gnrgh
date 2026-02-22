# encoding: utf-8
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('repository', pkey='id', name_long='!![en]Repository',
                        name_plural='!![en]Repositories', caption_field='name', archivable=True)
        self.sysFields(tbl)

        # Indexed fields (for queries/filters)
        tbl.column('github_id', dtype='L', unique=True, indexed=True, name_long='!![en]GitHub ID')
        tbl.column('name', name_long='!![en]Name')
        tbl.column('full_name', unique=True, indexed=True, name_long='!![en]Full Name')  # "org/repo"
        tbl.column('private', dtype='B', indexed=True, name_long='!![en]Private')
        tbl.column('archived', dtype='B', indexed=True, name_long='!![en]Archived')

        # Relation
        tbl.column('organization_id', size='22', group='_', name_long='!![en]Organization').relation(
            'organization.id', relation_name='repositories', mode='foreignkey', onDelete='cascade')

        # Info fields
        tbl.column('description', name_long='!![en]Description', name_short='!![en]Descr.')
        tbl.column('default_branch', name_long='!![en]Default Branch')
        tbl.column('html_url', name_long='!![en]URL')

        # Raw payload from GitHub API
        tbl.column('metadata', dtype='X', name_long='!![en]Metadata')

        # Internal editable fields (not synced from GitHub)
        tbl.column('webhook_sync', dtype='B', indexed=True,
                   name_long='!![en]Webhook Sync')  # Flag for automatic sync via webhooks
        tbl.column('repo_group', size=':32', name_long='!![en]Repository Group', batch_assign=True).relation(
            'repo_group.code', relation_name='repositories', mode='foreignkey', onDelete='setnull')
        tbl.column('closure_date', dtype='D', name_long='!![en]Closure Date', batch_assign=True)
        tbl.column('closure_reason', name_long='!![en]Closure Reason', batch_assign=True)
        tbl.column('internal_notes', name_long='!![en]Internal Notes', batch_assign=True)

        # Commit policy (overrides organization level)
        tbl.column('commit_policy', name_long='!![en]Commit Policy')

        # Sync tracking
        tbl.column('last_sync_ts', dtype='DH', name_long='!![en]Last Sync')

        # Reference fields (extracted from metadata, purely informational)
        tbl.bagItemColumn('avatar_url', bagcolumn='$metadata', itempath='owner.avatar_url', name_long='!![en]Avatar URL')
        tbl.bagItemColumn('github_created_at', bagcolumn='$metadata', itempath='created_at', name_long='!![en]GitHub Created')
        tbl.bagItemColumn('github_updated_at', bagcolumn='$metadata', itempath='updated_at', name_long='!![en]GitHub Updated')
        tbl.bagItemColumn('pushed_at', bagcolumn='$metadata', itempath='pushed_at', name_long='!![en]Last Push')

        # Formula columns for counts
        tbl.formulaColumn('open_issues_count',
            select=dict(table='gnrgh.issue',
                        columns='COUNT(*)',
                        where="$repository_id=#THIS.id AND $state='open'"),
            dtype='L', name_long='!![en]Open Issues')

        tbl.formulaColumn('open_pull_requests_count',
            select=dict(table='gnrgh.pull_request',
                        columns='COUNT(*)',
                        where="$repository_id=#THIS.id AND $state='open'"),
            dtype='L', name_long='!![en]Open PRs')

        # Formula column for current user connection
        tbl.formulaColumn('is_user_connected',
            exists=dict(table='gnrgh.gh_user_connection',
                        where='$repository_id=#THIS.id AND $gh_user_id=:env_gh_user_id'),
            dtype='B', name_long='!![en]Connected')

        # Formula columns for user activity on open issues/PRs
        tbl.formulaColumn('has_user_open_issues',
            exists=dict(table='gnrgh.issue',
                        where="$repository_id=#THIS.id AND $state='open' AND $author_id=:env_gh_user_id"),
            dtype='B', name_long='!![en]Has My Issues')

        tbl.formulaColumn('has_user_assigned_issues',
            exists=dict(table='gnrgh.gh_user_connection',
                        where="@issue_id.repository_id=#THIS.id AND @issue_id.state='open' AND $gh_user_id=:env_gh_user_id"),
            dtype='B', name_long='!![en]Has Assigned Issues')

        tbl.formulaColumn('has_user_open_prs',
            exists=dict(table='gnrgh.pull_request',
                        where="$repository_id=#THIS.id AND $state='open' AND $author_id=:env_gh_user_id"),
            dtype='B', name_long='!![en]Has My PRs')

        tbl.formulaColumn('has_user_assigned_prs',
            exists=dict(table='gnrgh.gh_user_connection',
                        where="@pull_request_id.repository_id=#THIS.id AND @pull_request_id.state='open' AND $gh_user_id=:env_gh_user_id"),
            dtype='B', name_long='!![en]Has Assigned PRs')

        tbl.formulaColumn('needs_attention',
            '$has_user_open_issues OR $has_user_assigned_issues OR $has_user_open_prs OR $has_user_assigned_prs',
            dtype='B', name_long='!![en]Needs Attention')

        tbl.formulaColumn('has_pending_events',
            exists=dict(table='gnrgh.webhook_event',
                        where='$repo_id=#THIS.id AND $received_at > #THIS.last_sync_ts'),
            dtype='B', name_long='!![en]Pending Events')

        tbl.formulaColumn('branch_count',
            select=dict(table='gnrgh.branch',
                        columns='COUNT(*)',
                        where='$repository_id=#THIS.id'),
            dtype='L', name_long='!![en]Branches')

        tbl.formulaColumn('last_commit_ts',
            select=dict(table='gnrgh.commit',
                        columns='MAX($author_date)',
                        where='@branch_id.repository_id=#THIS.id'),
            dtype='DH', name_long='!![en]Last Commit')

    def importRepository(self, remote_repo_data, pkey=None, organization_id=None):
        github_id = remote_repo_data['id']
        kw = dict(pkey=pkey) if pkey else dict(github_id=github_id, insertMissing=True)
        with self.recordToUpdate(**kw) as repo_rec:
            repo_rec['github_id'] = github_id
            repo_rec['name'] = remote_repo_data['name']
            repo_rec['full_name'] = remote_repo_data['full_name']
            repo_rec['description'] = remote_repo_data['description']
            repo_rec['private'] = remote_repo_data.get('private', False)
            repo_rec['archived'] = remote_repo_data.get('archived', False)
            repo_rec['default_branch'] = remote_repo_data.get('default_branch')
            repo_rec['html_url'] = remote_repo_data.get('html_url')
            repo_rec['organization_id'] = repo_rec['organization_id'] or organization_id
            repo_rec['metadata'] = Bag(remote_repo_data)

        repository_id = repo_rec['id']

        # Import owner as gh_user and create connection
        owner_data = remote_repo_data.get('owner')
        if owner_data:
            user_tbl = self.db.table('gnrgh.gh_user')
            connection_tbl = self.db.table('gnrgh.gh_user_connection')
            owner_user_id = user_tbl.importUser(owner_data)
            if owner_user_id:
                connection_tbl.addConnection(
                    gh_user_id=owner_user_id,
                    repo_role_code='owner',
                    repository_id=repository_id
                )

        return repository_id

    def processEvent(self, payload, action=None):
        """Process a webhook event for repositories.

        Args:
            payload: Complete webhook payload dict
            action: Action type (created, deleted, archived, etc.)

        Returns:
            The pkey of the created/updated repository, or None if not processed
        """
        repo_data = payload.get('repository')
        if not repo_data:
            return None

        # Get organization_id if present
        organization_id = None
        org_data = payload.get('organization')
        if org_data:
            org_id = org_data.get('id')
            org_rec = self.db.table('gnrgh.organization').query(
                where='$github_id=:gid', gid=org_id
            ).fetch()
            if org_rec:
                organization_id = org_rec[0]['id']

        # Import/update the repository
        repository_id = self.importRepository(repo_data, organization_id=organization_id)

        # On push events, update the branch commit_sha
        if payload.get('ref', '').startswith('refs/heads/'):
            branch_name = payload['ref'].replace('refs/heads/', '')
            commit_sha = payload.get('after')
            if repository_id and commit_sha:
                self.db.table('gnrgh.branch').updateCommitSha(
                    repository_id=repository_id,
                    branch_name=branch_name,
                    commit_sha=commit_sha
                )

        return repository_id

# encoding: utf-8

from datetime import datetime, timezone


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('branch', pkey='id', name_long='!![en]Branch',
                        name_plural='!![en]Branches', caption_field='name')
        self.sysFields(tbl)

        tbl.column('repository_id', size='22', group='_', name_long='!![en]Repository').relation(
            'repository.id', relation_name='branches', mode='foreignkey', onDelete='cascade')
        tbl.column('name', name_long='!![en]Name', validate_notnull=True)
        tbl.column('commit_sha', name_long='!![en]Commit SHA')
        tbl.column('protected', dtype='B', name_long='!![en]Protected')
        tbl.column('is_default', dtype='B', name_long='!![en]Default Branch')

        # Commit policy (overrides repository level)
        tbl.column('commit_policy', name_long='!![en]Commit Policy')
        tbl.column('last_sync_ts', dtype='DHZ', name_long='!![en]Last Sync')
        tbl.column('pushed_at', dtype='DHZ', name_long='!![en]Last Push')

        tbl.compositeColumn('repo_branch', columns='repository_id,name', unique=True)

        # Alias columns
        tbl.aliasColumn('organization_name', '@repository_id.@organization_id.login',
                        name_long='!![en]Organization')
        tbl.aliasColumn('repo_name', '@repository_id.name',
                        name_long='!![en]Repository Name')
        tbl.aliasColumn('repo_full_name', '@repository_id.full_name',
                        name_long='!![en]Repository')
        tbl.aliasColumn('repo_group', '@repository_id.repo_group',
                        name_long='!![en]Group')

        tbl.formulaColumn('last_commit_ts',
            select=dict(table='gnrgh.branch_commit',
                        columns='MAX(@commit_id.author_date)',
                        where='$branch_id=#THIS.id'),
            dtype='DHZ', name_long='!![en]Last Commit')

        tbl.formulaColumn('commit_count',
            select=dict(table='gnrgh.branch_commit',
                        columns='COUNT($id)',
                        where='$branch_id=#THIS.id'),
            dtype='L', name_long='!![en]Commits')

    def importBranch(self, remote_branch_data, repository_id=None):
        """Import a single branch from GitHub API data.

        Args:
            remote_branch_data: dict from GitHub branches API
            repository_id: pkey of the parent repository

        Returns:
            The pkey of the created/updated branch record
        """
        name = remote_branch_data['name']
        with self.recordToUpdate(repository_id=repository_id, name=name,
                                 insertMissing=True) as branch_rec:
            branch_rec['repository_id'] = repository_id
            branch_rec['name'] = name
            commit_data = remote_branch_data.get('commit', {})
            branch_rec['commit_sha'] = commit_data.get('sha') if isinstance(commit_data, dict) else None
            branch_rec['protected'] = remote_branch_data.get('protected', False)
        return branch_rec['id']

    def importBranches(self, branches_data, repository_id=None):
        """Import all branches for a repository.

        Args:
            branches_data: list of dicts from GitHub branches API
            repository_id: pkey of the parent repository

        Returns:
            Number of branches imported
        """
        imported_names = set()
        for branch_data in branches_data:
            self.importBranch(branch_data, repository_id=repository_id)
            imported_names.add(branch_data['name'])

        # Mark default branch
        repo_rec = self.db.table('gnrgh.repository').record(repository_id).output('dict')
        default_branch = repo_rec.get('default_branch')
        if default_branch:
            existing = self.query(
                where='$repository_id=:repo_id',
                repo_id=repository_id
            ).fetch()
            for rec in existing:
                is_default = rec['name'] == default_branch
                if rec['is_default'] != is_default:
                    with self.recordToUpdate(pkey=rec['id']) as r:
                        r['is_default'] = is_default

        # Remove branches that no longer exist on remote
        existing = self.query(
            where='$repository_id=:repo_id',
            repo_id=repository_id
        ).fetch()
        for rec in existing:
            if rec['name'] not in imported_names:
                self.delete(rec)

        self.db.commit()
        return len(imported_names)

    def processEvent(self, payload, action=None):
        """Process webhook events for branches.

        Handles 'create' and 'delete' events with ref_type='branch',
        and 'push' events to update commit_sha.
        """
        event_type = payload.get('ref_type')
        repo_data = payload.get('repository')
        if not repo_data:
            return None

        # Find the repository
        repo_github_id = repo_data['id']
        repo_tbl = self.db.table('gnrgh.repository')
        repo_recs = repo_tbl.query(
            where='$github_id=:gid', gid=repo_github_id
        ).fetch()
        if not repo_recs:
            return None
        repository_id = repo_recs[0]['id']

        if action == 'create' and event_type == 'branch':
            branch_name = payload.get('ref')
            if branch_name:
                with self.recordToUpdate(repository_id=repository_id, name=branch_name,
                                         insertMissing=True) as branch_rec:
                    branch_rec['repository_id'] = repository_id
                    branch_rec['name'] = branch_name
                    branch_rec['commit_sha'] = None  # will be set by the first push event
                self.db.commit()
                return branch_rec['id']

        elif action == 'delete' and event_type == 'branch':
            branch_name = payload.get('ref')
            if branch_name:
                recs = self.query(
                    where='$repository_id=:repo_id AND $name=:bname',
                    repo_id=repository_id, bname=branch_name
                ).fetch()
                for rec in recs:
                    self.delete(rec)
                self.db.commit()

        return None

    def updateCommitSha(self, repository_id=None, branch_name=None, commit_sha=None):
        """Update the commit SHA for a branch after a push event.

        Creates the branch if it doesn't exist yet (e.g. first push
        on a new branch without a preceding 'create' event).
        """
        with self.recordToUpdate(repository_id=repository_id, name=branch_name,
                                 insertMissing=True) as branch_rec:
            branch_rec['repository_id'] = repository_id
            branch_rec['name'] = branch_name
            branch_rec['commit_sha'] = commit_sha
            branch_rec['pushed_at'] = datetime.now(timezone.utc)
        self.db.commit()
        return branch_rec['id']

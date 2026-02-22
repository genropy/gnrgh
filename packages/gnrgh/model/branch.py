# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('branch', pkey='id', name_long='!![en]Branch',
                        name_plural='!![en]Branches', caption_field='name')
        self.sysFields(tbl)

        tbl.column('repository_id', size='22', group='_', name_long='!![en]Repository').relation(
            'repository.id', relation_name='branches', mode='foreignkey', onDelete='cascade')
        tbl.column('name', name_long='!![en]Name', validate_notnull=True)
        tbl.column('commit_sha', name_long='!![en]Commit SHA')
        tbl.column('last_commit_ts', dtype='DH', name_long='!![en]Last Commit')
        tbl.column('protected', dtype='B', name_long='!![en]Protected')
        tbl.column('is_default', dtype='B', name_long='!![en]Default Branch')

        # Commit policy (overrides repository level)
        tbl.column('commit_policy', name_long='!![en]Commit Policy')

        tbl.compositeColumn('repo_branch', columns='repository_id,name', unique=True)

        # Formula columns
        tbl.formulaColumn('repo_full_name',
            '@repository_id.full_name',
            name_long='!![en]Repository')

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
                    branch_rec['commit_sha'] = payload.get('master_branch')
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
        """Update the commit SHA for a branch after a push event."""
        recs = self.query(
            where='$repository_id=:repo_id AND $name=:bname',
            repo_id=repository_id, bname=branch_name
        ).fetch()
        if recs:
            with self.recordToUpdate(pkey=recs[0]['id']) as branch_rec:
                branch_rec['commit_sha'] = commit_sha
            self.db.commit()
            return recs[0]['id']
        return None

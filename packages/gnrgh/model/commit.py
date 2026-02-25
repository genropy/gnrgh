# encoding: utf-8

from dateutil.parser import parse as parse_date


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('commit', pkey='id', name_long='!![en]Commit',
                        name_plural='!![en]Commits', caption_field='sha')
        self.sysFields(tbl)

        tbl.column('repository_id', size='22', group='_',
                   name_long='!![en]Repository').relation(
            'repository.id', relation_name='commits',
            mode='foreignkey', onDelete='cascade')
        tbl.column('sha', name_long='!![en]SHA', validate_notnull=True, indexed=True)
        tbl.column('author_name', name_long='!![en]Author Name')
        tbl.column('author_email', name_long='!![en]Author Email', indexed=True)
        tbl.column('author_date', dtype='DH', name_long='!![en]Author Date', indexed=True)
        tbl.column('message', dtype='T', name_long='!![en]Message', ext_ltx='*', ltx_documentRegister=dict(preprocess=False, document_type='commit_message'))
        tbl.column('files_changed', dtype='I', name_long='!![en]Files Changed')

        tbl.index('repository_id,sha', unique=True)

        # Formula columns
        tbl.formulaColumn('repo_full_name',
            '@repository_id.full_name',
            name_long='!![en]Repository')

        tbl.formulaColumn('branch_names',
            select=dict(table='gnrgh.branch_commit',
                        columns="STRING_AGG(@branch_id.name, ', ')",
                        where='$commit_id=#THIS.id'),
            name_long='!![en]Branches')

    def importCommit(self, commit_data, repository_id=None, branch_id=None):
        """Import a single commit from GitHub API data.

        Args:
            commit_data: dict from GitHub commits API
            repository_id: pkey of the parent repository
            branch_id: optional pkey of the branch (creates link in branch_commit)

        Returns:
            The pkey of the created/updated commit record
        """
        sha = commit_data['sha']
        commit_info = commit_data.get('commit', {})
        author_info = commit_info.get('author', {})
        with self.recordToUpdate(repository_id=repository_id, sha=sha,
                                 insertMissing=True) as rec:
            rec['repository_id'] = repository_id
            rec['sha'] = sha
            rec['author_name'] = author_info.get('name')
            rec['author_email'] = author_info.get('email')
            date_str = author_info.get('date')
            if date_str:
                rec['author_date'] = parse_date(date_str)
            message = commit_info.get('message')
            rec['message'] = message
            rec['message_text'] = message
            stats = commit_data.get('stats', {})
            if stats:
                rec['files_changed'] = stats.get('total')
        commit_id = rec['id']
        if branch_id:
            bc_tbl = self.db.table('gnrgh.branch_commit')
            bc_tbl.linkBranchCommit(branch_id=branch_id, commit_id=commit_id)
        return commit_id

    def importCommitFromPush(self, push_commit, repository_id=None, branch_id=None):
        """Import a single commit from a push webhook payload.

        The push payload format differs from the REST API format:
        - Push: commit['id'] (sha), commit['author']['name'], commit['message']
        - API:  commit['sha'], commit['commit']['author']['name']

        Args:
            push_commit: dict from push payload commits array
            repository_id: pkey of the parent repository
            branch_id: optional pkey of the branch

        Returns:
            The pkey of the created/updated commit record
        """
        sha = push_commit.get('id')
        if not sha:
            return None
        author_info = push_commit.get('author', {})
        with self.recordToUpdate(repository_id=repository_id, sha=sha,
                                 insertMissing=True) as rec:
            rec['repository_id'] = repository_id
            rec['sha'] = sha
            rec['author_name'] = author_info.get('name')
            rec['author_email'] = author_info.get('email')
            timestamp = push_commit.get('timestamp')
            if timestamp:
                rec['author_date'] = parse_date(timestamp)
            rec['message'] = push_commit.get('message')
            # Count files changed from added/removed/modified arrays
            files_changed = (len(push_commit.get('added', []))
                           + len(push_commit.get('removed', []))
                           + len(push_commit.get('modified', [])))
            if files_changed:
                rec['files_changed'] = files_changed
        commit_id = rec['id']
        if branch_id:
            bc_tbl = self.db.table('gnrgh.branch_commit')
            bc_tbl.linkBranchCommit(branch_id=branch_id, commit_id=commit_id)
        return commit_id

    def importCommits(self, commits_data, repository_id=None, branch_id=None):
        """Import commits for a repository.

        Args:
            commits_data: list of dicts from GitHub commits API
            repository_id: pkey of the parent repository
            branch_id: optional pkey of the branch (creates links in branch_commit)

        Returns:
            Number of commits imported
        """
        imported_shas = set()
        for commit_data in commits_data:
            self.importCommit(commit_data, repository_id=repository_id,
                             branch_id=branch_id)
            imported_shas.add(commit_data['sha'])
        return len(imported_shas)

# encoding: utf-8

from dateutil.parser import parse as parse_date


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('commit', pkey='id', name_long='!![en]Commit',
                        name_plural='!![en]Commits', caption_field='sha')
        self.sysFields(tbl)

        tbl.column('branch_id', size='22', group='_', name_long='!![en]Branch').relation(
            'branch.id', relation_name='commits', mode='foreignkey', onDelete='cascade')
        tbl.column('sha', name_long='!![en]SHA', validate_notnull=True, indexed=True)
        tbl.column('author_name', name_long='!![en]Author Name')
        tbl.column('author_email', name_long='!![en]Author Email', indexed=True)
        tbl.column('author_date', dtype='DH', name_long='!![en]Author Date', indexed=True)
        tbl.column('message', dtype='T', name_long='!![en]Message')
        tbl.column('files_changed', dtype='I', name_long='!![en]Files Changed')

        tbl.index('branch_id,sha', unique=True)

        # Formula columns
        tbl.formulaColumn('repo_full_name',
            '@branch_id.@repository_id.full_name',
            name_long='!![en]Repository')
        tbl.formulaColumn('branch_name',
            '@branch_id.name',
            name_long='!![en]Branch')

    def importCommit(self, commit_data, branch_id=None):
        """Import a single commit from GitHub API data.

        Args:
            commit_data: dict from GitHub commits API
            branch_id: pkey of the parent branch

        Returns:
            The pkey of the created/updated commit record
        """
        sha = commit_data['sha']
        commit_info = commit_data.get('commit', {})
        author_info = commit_info.get('author', {})
        with self.recordToUpdate(branch_id=branch_id, sha=sha,
                                 insertMissing=True) as rec:
            rec['branch_id'] = branch_id
            rec['sha'] = sha
            rec['author_name'] = author_info.get('name')
            rec['author_email'] = author_info.get('email')
            date_str = author_info.get('date')
            if date_str:
                rec['author_date'] = parse_date(date_str)
            rec['message'] = commit_info.get('message')
            stats = commit_data.get('stats', {})
            if stats:
                rec['files_changed'] = stats.get('total')
        return rec['id']

    def importCommits(self, commits_data, branch_id=None):
        """Import commits for a branch.

        Args:
            commits_data: list of dicts from GitHub commits API
            branch_id: pkey of the parent branch

        Returns:
            Number of commits imported
        """
        imported_shas = set()
        for commit_data in commits_data:
            self.importCommit(commit_data, branch_id=branch_id)
            imported_shas.add(commit_data['sha'])
        return len(imported_shas)

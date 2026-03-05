# encoding: utf-8
from gnr.core.gnrbag import Bag

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('issue', pkey='id',
                        name_long='!![en]Issue',
                        name_plural='!![en]Issues',
                        caption_field='title')
        self.sysFields(tbl)

        # GitHub unique identifier
        tbl.column('github_id', dtype='L', unique=True, indexed=True,
                   name_long='!![en]GitHub ID')

        # Relations
        tbl.column('repository_id', size='22', group='_',
                   name_long='!![en]Repository').relation(
            'repository.id', relation_name='issues',
            mode='foreignkey', onDelete='cascade')

        tbl.column('author_id', size='22', group='_',
                   name_long='!![en]Author').relation(
            'gh_user.id', relation_name='authored_issues',
            mode='foreignkey', onDelete='setnull')

        # Issue fields
        tbl.column('number', dtype='L', indexed=True,
                   name_long='!![en]Number')
        tbl.column('title', name_long='!![en]Title')
        tbl.column('body', name_long='!![en]Body', ext_ltx='*', ltx_documentRegister=dict(preprocess=False, document_type='issue'))
        tbl.column('state', size=':16', indexed=True,
                   name_long='!![en]State',values='open:Open,closed:Closed')  # open, closed
        tbl.column('state_reason', size=':32',
                   name_long='!![en]State Reason')  # completed, not_planned, reopened
        tbl.column('html_url', name_long='!![en]URL')

        # Timestamps from GitHub
        tbl.column('github_created_at', dtype='DH', indexed=True,
                   name_long='!![en]GitHub Created')
        tbl.column('github_updated_at', dtype='DH', indexed=True,
                   name_long='!![en]GitHub Updated')
        tbl.column('github_closed_at', dtype='DH',
                   name_long='!![en]GitHub Closed')

        # Raw payload from GitHub API
        tbl.column('metadata', dtype='X', name_long='!![en]Metadata')

        # Composite column for unique constraint on repository + number
        tbl.compositeColumn('repo_number_id', columns='repository_id,number', unique=True)

        # Calculated fields from metadata
        tbl.bagItemColumn('labels_json', bagcolumn='$metadata',
                          itempath='labels', name_long='!![en]Labels')
        tbl.bagItemColumn('milestone_title', bagcolumn='$metadata',
                          itempath='milestone.title', name_long='!![en]Milestone')
        tbl.bagItemColumn('comments_count', bagcolumn='$metadata',
                          itempath='comments', name_long='!![en]Comments')

        # Formula column for current user connection (author or assignee)
        tbl.formulaColumn('is_user_connected',
            exists=dict(table='gnrgh.gh_user_connection',
                        where='$issue_id=#THIS.id AND $gh_user_id=:env_gh_user_id'),
            dtype='B', name_long='!![en]Connected')

        tbl.formulaColumn('is_user_author',
            '$author_id=:env_gh_user_id',
            dtype='B', name_long='!![en]Author')

        tbl.formulaColumn('cnt_user',"CASE WHEN $is_user_connected IS TRUE THEN 1 ELSE 0 END",dtype='L',
                          name_long='!![en]Mine Cnt.')


    def importIssue(self, issue_data, repository_id=None, pkey=None):
        """Import or update an issue from GitHub API payload.

        Args:
            issue_data: dict from GitHub API
            repository_id: FK to repository (required for new records)
            pkey: optional existing record pkey

        Returns:
            The pkey of the imported/updated record, or None if this is a PR
        """
        # Skip if this is actually a PR (has pull_request field)
        if issue_data.get('pull_request'):
            return None

        github_id = issue_data['id']
        kw = dict(pkey=pkey) if pkey else dict(github_id=github_id, insertMissing=True)

        # Import/update author
        author_id = None
        user_data = issue_data.get('user')
        if user_data:
            author_id = self.db.table('gnrgh.gh_user').importUser(user_data)

        with self.recordToUpdate(**kw) as rec:
            rec['github_id'] = github_id
            rec['repository_id'] = rec['repository_id'] or repository_id
            rec['author_id'] = author_id
            rec['number'] = issue_data['number']
            rec['title'] = issue_data['title']
            rec['body'] = issue_data.get('body')
            rec['state'] = issue_data['state']
            rec['state_reason'] = issue_data.get('state_reason')
            rec['html_url'] = issue_data.get('html_url')
            rec['github_created_at'] = issue_data.get('created_at')
            rec['github_updated_at'] = issue_data.get('updated_at')
            rec['github_closed_at'] = issue_data.get('closed_at')
            rec['metadata'] = Bag(issue_data)

        issue_pkey = rec['id']

        # Import assignees
        self._importAssignees(issue_pkey, issue_data.get('assignees', []))

        return issue_pkey

    def _importAssignees(self, issue_id, assignees_data):
        """Import assignees for an issue.

        Args:
            issue_id: pkey of the issue
            assignees_data: list of user dicts from GitHub API
        """
        connection_tbl = self.db.table('gnrgh.gh_user_connection')
        user_tbl = self.db.table('gnrgh.gh_user')

        connection_tbl.syncAssignees(
            assignees_data=assignees_data,
            user_tbl=user_tbl,
            issue_id=issue_id
        )

    def processEvent(self, payload, action=None):
        """Process a webhook event for issues.

        Args:
            payload: Complete webhook payload dict
            action: Action type (opened, closed, edited, etc.)

        Returns:
            The pkey of the created/updated issue, or None if not processed
        """
        issue_data = payload.get('issue')
        if not issue_data:
            return None

        # Get repository_id from the payload
        repository_id = None
        repo_data = payload.get('repository')
        if repo_data:
            repo_id = repo_data.get('id')
            repo_rec = self.db.table('gnrgh.repository').query(
                where='$github_id=:gid', gid=repo_id
            ).fetch()
            if repo_rec:
                repository_id = repo_rec[0]['id']

        # Import/update the issue
        return self.importIssue(issue_data, repository_id=repository_id)

    def importComments(self, issue_id, comments_data):
        """Import comments for an issue from GitHub API payload.

        Args:
            issue_id: pkey of the issue
            comments_data: list of comment dicts from GitHub API

        Returns:
            List of imported comment pkeys
        """
        comment_tbl = self.db.table('gnrgh.issue_comment')
        return comment_tbl.importCommentsForIssue(comments_data, issue_id)

    def ltx_caption(self, record):
        repo_name = self.db.table('gnrgh.repository').readColumns(
            columns='$full_name', pkey=record['repository_id'])
        number = record.get('number') or '?'
        title = (record.get('title') or '')[:80]
        author_login = None
        if record.get('author_id'):
            author_login = self.db.table('gnrgh.gh_user').readColumns(
                columns='$login', pkey=record['author_id'])
        return dict(
            name='%s — #%s: %s' % (repo_name or '?', number, title),
            gnrgh_repository_id=record['repository_id'],
            document_date=record.get('github_created_at'),
            author_name=author_login
        )

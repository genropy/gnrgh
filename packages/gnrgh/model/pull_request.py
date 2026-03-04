# encoding: utf-8
from gnr.core.gnrbag import Bag

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('pull_request', pkey='id',
                        name_long='!![en]Pull Request',
                        name_plural='!![en]Pull Requests',
                        caption_field='title')
        self.sysFields(tbl)

        # GitHub unique identifier
        tbl.column('github_id', dtype='L', unique=True, indexed=True,
                   name_long='!![en]GitHub ID')

        # Relations
        tbl.column('repository_id', size='22', group='_',
                   name_long='!![en]Repository').relation(
            'repository.id', relation_name='pull_requests',
            mode='foreignkey', onDelete='cascade')

        tbl.column('author_id', size='22', group='_',
                   name_long='!![en]Author').relation(
            'gh_user.id', relation_name='authored_pull_requests',
            mode='foreignkey', onDelete='setnull')

        # PR common fields
        tbl.column('number', dtype='L', indexed=True,
                   name_long='!![en]Number')
        tbl.column('title', name_long='!![en]Title')
        tbl.column('body', name_long='!![en]Body',
                   ext_ltx='*', ltx_documentRegister=dict(preprocess=False, document_type='pull_request'))
        tbl.column('state', size=':16', indexed=True,
                   name_long='!![en]State',values='open:Open,closed:Closed')  # open, closed
        tbl.column('html_url', name_long='!![en]URL')

        # PR-specific fields
        tbl.column('draft', dtype='B', indexed=True,
                   name_long='!![en]Draft')
        tbl.column('merged', dtype='B', indexed=True,
                   name_long='!![en]Merged')
        tbl.column('mergeable', dtype='B',
                   name_long='!![en]Mergeable')
        tbl.column('mergeable_state', size=':32',
                   name_long='!![en]Mergeable State')  # clean, dirty, blocked, etc.

        # Branch info
        tbl.column('head_ref', name_long='!![en]Head Branch')  # source branch
        tbl.column('head_sha', size=':40', name_long='!![en]Head SHA')
        tbl.column('base_ref', name_long='!![en]Base Branch')  # target branch
        tbl.column('base_sha', size=':40', name_long='!![en]Base SHA')

        # Merge info
        tbl.column('merge_commit_sha', size=':40',
                   name_long='!![en]Merge Commit SHA')

        # Timestamps from GitHub
        tbl.column('github_created_at', dtype='DH', indexed=True,
                   name_long='!![en]GitHub Created')
        tbl.column('github_updated_at', dtype='DH', indexed=True,
                   name_long='!![en]GitHub Updated')
        tbl.column('github_closed_at', dtype='DH',
                   name_long='!![en]GitHub Closed')
        tbl.column('github_merged_at', dtype='DH', indexed=True,
                   name_long='!![en]GitHub Merged')

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
        tbl.bagItemColumn('review_comments_count', bagcolumn='$metadata',
                          itempath='review_comments', name_long='!![en]Review Comments')
        tbl.bagItemColumn('commits_count', bagcolumn='$metadata',
                          itempath='commits', name_long='!![en]Commits')
        tbl.bagItemColumn('additions', bagcolumn='$metadata',
                          itempath='additions', name_long='!![en]Additions')
        tbl.bagItemColumn('deletions', bagcolumn='$metadata',
                          itempath='deletions', name_long='!![en]Deletions')
        tbl.bagItemColumn('changed_files', bagcolumn='$metadata',
                          itempath='changed_files', name_long='!![en]Changed Files')

        # Formula column for current user connection (author or assignee/reviewer)
        tbl.formulaColumn('is_user_connected',
            exists=dict(table='gnrgh.gh_user_connection',
                        where='$pull_request_id=#THIS.id AND $gh_user_id=:env_gh_user_id'),
            dtype='B', name_long='!![en]Connected')

        tbl.formulaColumn('is_user_author',
            '$author_id=:env_gh_user_id',
            dtype='B', name_long='!![en]Author')
        tbl.formulaColumn('cnt_user',"CASE WHEN $is_user_connected IS TRUE THEN 1 ELSE 0 END",dtype='L',
                          name_long='!![en]Mine Cnt.')


    def importPullRequest(self, pr_data, repository_id=None, pkey=None):
        """Import or update a pull request from GitHub API payload.

        Args:
            pr_data: dict from GitHub API (from /pulls endpoint)
            repository_id: FK to repository (required for new records)
            pkey: optional existing record pkey

        Returns:
            The pkey of the imported/updated record
        """
        github_id = pr_data['id']
        kw = dict(pkey=pkey) if pkey else dict(github_id=github_id, insertMissing=True)

        # Import/update author
        author_id = None
        user_data = pr_data.get('user')
        if user_data:
            author_id = self.db.table('gnrgh.gh_user').importUser(user_data)

        with self.recordToUpdate(**kw) as rec:
            rec['github_id'] = github_id
            rec['repository_id'] = rec['repository_id'] or repository_id
            rec['author_id'] = author_id
            rec['number'] = pr_data['number']
            rec['title'] = pr_data['title']
            rec['body'] = pr_data.get('body')
            rec['state'] = pr_data['state']
            rec['html_url'] = pr_data.get('html_url')

            # PR-specific fields
            rec['draft'] = pr_data.get('draft', False)
            rec['merged'] = pr_data.get('merged', False)
            rec['mergeable'] = pr_data.get('mergeable')
            rec['mergeable_state'] = pr_data.get('mergeable_state')

            # Branch info
            head = pr_data.get('head', {})
            base = pr_data.get('base', {})
            rec['head_ref'] = head.get('ref')
            rec['head_sha'] = head.get('sha')
            rec['base_ref'] = base.get('ref')
            rec['base_sha'] = base.get('sha')

            rec['merge_commit_sha'] = pr_data.get('merge_commit_sha')

            # Timestamps
            rec['github_created_at'] = pr_data.get('created_at')
            rec['github_updated_at'] = pr_data.get('updated_at')
            rec['github_closed_at'] = pr_data.get('closed_at')
            rec['github_merged_at'] = pr_data.get('merged_at')

            rec['metadata'] = Bag(pr_data)

        pr_pkey = rec['id']

        # Import assignees
        self._importAssignees(pr_pkey, pr_data.get('assignees', []))

        return pr_pkey

    def _importAssignees(self, pull_request_id, assignees_data):
        """Import assignees for a pull request.

        Args:
            pull_request_id: pkey of the pull request
            assignees_data: list of user dicts from GitHub API
        """
        connection_tbl = self.db.table('gnrgh.gh_user_connection')
        user_tbl = self.db.table('gnrgh.gh_user')

        connection_tbl.syncAssignees(
            assignees_data=assignees_data,
            user_tbl=user_tbl,
            pull_request_id=pull_request_id
        )

    def processEvent(self, payload, action=None):
        """Process a webhook event for pull requests.

        Args:
            payload: Complete webhook payload dict
            action: Action type (opened, closed, merged, etc.)

        Returns:
            The pkey of the created/updated pull request, or None if not processed
        """
        pr_data = payload.get('pull_request')
        if not pr_data:
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

        # Import/update the pull request
        return self.importPullRequest(pr_data, repository_id=repository_id)

    def ltx_caption(self, record):
        repo_name = self.db.table('gnrgh.repository').readColumns(
            columns='$full_name', pkey=record['repository_id'])
        number = record.get('number') or '?'
        title = (record.get('title') or '')[:80]
        return dict(
            name='%s — PR #%s: %s' % (repo_name or '?', number, title),
            gnrgh_repository_id=record['repository_id']
        )

# encoding: utf-8
from gnr.core.gnrbag import Bag

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('issue_comment', pkey='id',
                        name_long='!![en]Issue Comment',
                        name_plural='!![en]Issue Comments',
                        caption_field='body_preview')
        self.sysFields(tbl)

        # GitHub unique identifier
        tbl.column('github_id', dtype='L', unique=True, indexed=True,
                   name_long='!![en]GitHub ID')

        # Relations
        tbl.column('issue_id', size='22', group='_',
                   name_long='!![en]Issue').relation(
            'issue.id', relation_name='comments',
            mode='foreignkey', onDelete='cascade')

        tbl.column('author_id', size='22', group='_',
                   name_long='!![en]Author').relation(
            'gh_user.id', relation_name='issue_comments',
            mode='foreignkey', onDelete='setnull')

        # Comment fields
        tbl.column('body', name_long='!![en]Body', ext_ltx='*', ltx_documentRegister=dict(preprocess=False, document_type='issue_comment'))
        tbl.column('html_url', name_long='!![en]URL')

        # Timestamps from GitHub
        tbl.column('github_created_at', dtype='DHZ', indexed=True,
                   name_long='!![en]Created')
        tbl.column('github_updated_at', dtype='DHZ',
                   name_long='!![en]Updated')

        # Raw payload from GitHub API
        tbl.column('metadata', dtype='X', name_long='!![en]Metadata')

        # Formula column for body preview (first 100 chars)
        tbl.formulaColumn('body_preview',
                          "SUBSTRING($body, 1, 100)",
                          name_long='!![en]Preview')

    def importComment(self, comment_data, issue_id=None, pkey=None):
        """Import or update a comment from GitHub API payload.

        Args:
            comment_data: dict from GitHub API
            issue_id: FK to issue (required for new records)
            pkey: optional existing record pkey

        Returns:
            The pkey of the imported/updated record
        """
        github_id = comment_data['id']
        kw = dict(pkey=pkey) if pkey else dict(github_id=github_id, insertMissing=True)

        # Import/update author
        author_id = None
        user_data = comment_data.get('user')
        if user_data:
            author_id = self.db.table('gnrgh.gh_user').importUser(user_data)

        with self.recordToUpdate(**kw) as rec:
            rec['github_id'] = github_id
            rec['issue_id'] = rec['issue_id'] or issue_id
            rec['author_id'] = author_id
            rec['body'] = comment_data.get('body')
            rec['html_url'] = comment_data.get('html_url')
            rec['github_created_at'] = comment_data.get('created_at')
            rec['github_updated_at'] = comment_data.get('updated_at')
            rec['metadata'] = Bag(comment_data)

        return rec['id']

    def importCommentsForIssue(self, comments_data, issue_id):
        """Import all comments for an issue.

        Args:
            comments_data: list of comment dicts from GitHub API
            issue_id: FK to issue

        Returns:
            List of imported comment pkeys
        """
        imported = []
        for comment_data in comments_data:
            pkey = self.importComment(comment_data, issue_id=issue_id)
            if pkey:
                imported.append(pkey)
        return imported

    def processEvent(self, payload, action=None):
        """Process a webhook event for issue comments.

        Args:
            payload: Complete webhook payload dict
            action: Action type (created, edited, deleted)

        Returns:
            The pkey of the created/updated comment, or None if not processed
        """
        comment_data = payload.get('comment')
        if not comment_data:
            return None

        if action == 'deleted':
            # Remove deleted comment
            github_id = comment_data.get('id')
            if github_id:
                self.deleteSelection(where='$github_id=:gid', gid=github_id)
            return None

        # Get issue_id from the payload
        issue_id = None
        issue_data = payload.get('issue')
        if issue_data:
            issue_github_id = issue_data.get('id')
            issue_rec = self.db.table('gnrgh.issue').query(
                columns='$id',
                where='$github_id=:gid', gid=issue_github_id
            ).fetch()
            if issue_rec:
                issue_id = issue_rec[0]['id']

        if not issue_id:
            return None

        # Import/update the comment
        return self.importComment(comment_data, issue_id=issue_id)

    def ltx_caption(self, record):
        issue_tbl = self.db.table('gnrgh.issue')
        issue_number, repository_id = issue_tbl.readColumns(
            columns='$number,$repository_id',
            pkey=record['issue_id'])
        repo_name = self.db.table('gnrgh.repository').readColumns(
            columns='$full_name', pkey=repository_id)
        body_preview = (record.get('body') or '')[:80]
        author_login = None
        if record.get('author_id'):
            author_login = self.db.table('gnrgh.gh_user').readColumns(
                columns='$login', pkey=record['author_id'])
        return dict(
            name='%s — Issue #%s comment: %s' % (repo_name or '?', issue_number or '?', body_preview),
            gnrgh_repository_id=repository_id,
            document_date=record.get('github_created_at'),
            author_name=author_login
        )

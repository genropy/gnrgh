# encoding: utf-8
from gnr.core.gnrbag import Bag

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('gh_user', pkey='id',
                        name_long='!![en]GitHub User',
                        name_plural='!![en]GitHub Users',
                        caption_field='login')
        self.sysFields(tbl)

        # GitHub unique identifier (permanent, never changes)
        tbl.column('github_id', dtype='L', unique=True, indexed=True,
                   name_long='!![en]GitHub ID')

        # User info (login can change, but github_id is permanent)
        tbl.column('login', indexed=True, name_long='!![en]Login name')
        tbl.column('avatar_url', name_long='!![en]Avatar URL')
        tbl.column('html_url', name_long='!![en]Profile URL')
        tbl.column('user_type', size=':32', indexed=True,
                   name_long='!![en]Type')  # 'User' or 'Organization'

        # Raw payload from GitHub API
        tbl.column('metadata', dtype='X', name_long='!![en]Metadata')

        #formule and alias
        tbl.formulaColumn('adm_user_id','@adm_user.id',name_long='!![en]Adm User')

    def importUser(self, user_data):
        """Import or update a GitHub user from any API payload containing user data.

        Args:
            user_data: dict with at least 'id' and 'login' fields

        Returns:
            The pkey of the imported/updated record, or None if no valid data
        """
        if not user_data or not user_data.get('id'):
            return None

        github_id = user_data['id']

        with self.recordToUpdate(github_id=github_id, insertMissing=True) as rec:
            rec['github_id'] = github_id
            rec['login'] = user_data.get('login')
            rec['avatar_url'] = user_data.get('avatar_url')
            rec['html_url'] = user_data.get('html_url')
            rec['user_type'] = user_data.get('type', 'User')
            rec['metadata'] = Bag(user_data)

        return rec['id']

    def getUserPkey(self, user_data):
        """Get or create a GitHub user and return its pkey.

        Args:
            user_data: dict with at least 'id' field

        Returns:
            The pkey of the user record, or None if no valid data
        """
        if not user_data or not user_data.get('id'):
            return None

        github_id = user_data['id']

        # Try to find existing user
        existing = self.query(
            columns='$id',
            where='$github_id=:github_id',
            github_id=github_id
        ).fetch()

        if existing:
            return existing[0]['id']

        # Create new user
        return self.importUser(user_data)

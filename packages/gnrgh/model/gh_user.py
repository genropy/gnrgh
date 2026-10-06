# encoding: utf-8
from gnr.core.gnrbag import Bag

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('gh_user', pkey='id',
                        name_long='!![en]GitHub User',
                        name_plural='!![en]GitHub Users',
                        caption_field='login')
        self.sysFields(tbl)

        # Identity on its git server: github_id is permanent and unique
        # within the git_host (every server numbers its accounts from 1)
        tbl.column('git_host_id', size='22', group='_', name_long='!![en]Git Host').relation(
            'git_host.id', relation_name='users', mode='foreignkey', onDelete='raise')
        tbl.column('github_id', dtype='L', indexed=True, name_long='!![en]GitHub ID')
        tbl.compositeColumn('host_github_id', columns='git_host_id,github_id', unique=True)

        # User info (login can change, but github_id is permanent)
        tbl.column('login', indexed=True, name_long='!![en]Login name')
        tbl.column('avatar_url', name_long='!![en]Avatar URL')
        tbl.column('html_url', name_long='!![en]Profile URL')
        tbl.column('user_type', size=':32', indexed=True,
                   name_long='!![en]Type')  # 'User' or 'Organization'

        # Raw payload from GitHub API
        tbl.column('metadata', dtype='X', name_long='!![en]Metadata')

        # The application user behind the account: one adm.user has many
        # accounts, at most one per git_host
        tbl.column('adm_user_id', size='22', group='_', name_long='!![en]Adm User').relation(
            'adm.user.id', relation_name='gh_accounts', mode='foreignkey', onDelete='setnull')
        tbl.compositeColumn('adm_user_host', columns='adm_user_id,git_host_id', unique=True)

    def importUser(self, user_data, git_host_id=None):
        """Import or update an account from any API payload containing user data.

        Args:
            user_data: dict with at least 'id' and 'login' fields
            git_host_id: the server of user_data

        Returns:
            The pkey of the imported/updated record, or None if no valid data
        """
        if not user_data or not user_data.get('id'):
            return None
        if not git_host_id:
            raise ValueError('importUser needs the git_host_id of the account')

        github_id = user_data['id']

        with self.recordToUpdate(git_host_id=git_host_id, github_id=github_id,
                                 insertMissing=True) as rec:
            rec['git_host_id'] = git_host_id
            rec['github_id'] = github_id
            rec['login'] = user_data.get('login')
            rec['avatar_url'] = user_data.get('avatar_url')
            rec['html_url'] = user_data.get('html_url')
            rec['user_type'] = user_data.get('type', 'User')
            rec['metadata'] = Bag(user_data)

        return rec['id']

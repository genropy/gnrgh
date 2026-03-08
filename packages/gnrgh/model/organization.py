# encoding: utf-8
from gnr.core.gnrbag import Bag

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('organization', pkey='id', name_long='!![en]Organization',
                        name_plural='!![en]Organizations', caption_field='login')
        self.sysFields(tbl)

        # GitHub identity
        tbl.column('github_id', dtype='L', unique=True, name_long='!![en]GitHub ID',
                   indexed=True)
        tbl.column('login', unique=True, name_long='!![en]Login name', validate_notnull=True)
        tbl.column('name', name_long='!![en]Name')

        # Link to gh_user (org as user)
        tbl.column('org_user_id', size='22', group='_',
                   name_long='!![en]Org User').relation(
            'gh_user.id', relation_name='organizations',
            mode='foreignkey', onDelete='setnull')

        # URLs
        tbl.column('html_url', name_long='!![en]URL')
        tbl.column('avatar_url', name_long='!![en]Avatar URL')

        # GitHub timestamps
        tbl.column('github_created_at', dtype='DHZ', name_long='!![en]GitHub Created')
        tbl.column('github_updated_at', dtype='DHZ', name_long='!![en]GitHub Updated')

        # Raw payload
        tbl.column('raw', dtype='X', name_long='!![en]Raw Payload')

        # Commit policy (overrides global preference)
        tbl.column('commit_policy', name_long='!![en]Commit Policy')

        # Computed
        tbl.formulaColumn('num_repositories', select=dict(table='gnrgh.repository', columns='COUNT(*)',
                                                          where='$organization_id=#THIS.id'),
                          dtype='L', name_long='!![en]Num repositories')

    def importOrganization(self, org_data, pkey=None):
        """Import or update an organization from GitHub API payload.

        Args:
            org_data: dict from GitHub API
            pkey: optional existing record pkey

        Returns:
            The pkey of the imported/updated record
        """
        github_id = org_data['id']
        kw = dict(pkey=pkey) if pkey else dict(github_id=github_id, insertMissing=True)

        # Import org as gh_user (type=Organization)
        user_tbl = self.db.table('gnrgh.gh_user')
        org_user_id = user_tbl.importUser(org_data)

        with self.recordToUpdate(**kw) as rec:
            rec['github_id'] = github_id
            rec['login'] = org_data.get('login')
            rec['name'] = org_data.get('name')
            rec['html_url'] = org_data.get('html_url')
            rec['avatar_url'] = org_data.get('avatar_url')
            rec['github_created_at'] = org_data.get('created_at')
            rec['github_updated_at'] = org_data.get('updated_at')
            rec['org_user_id'] = org_user_id
            rec['raw'] = Bag(org_data)

        return rec['id']

    def processEvent(self, payload, action=None):
        """Process a webhook event for organizations.

        Args:
            payload: Complete webhook payload dict
            action: Action type

        Returns:
            The pkey of the created/updated organization, or None if not processed
        """
        org_data = payload.get('organization')
        if not org_data:
            return None

        # Import/update the organization
        return self.importOrganization(org_data)

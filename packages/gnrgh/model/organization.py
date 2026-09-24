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

        # Forge (empty api_url = GitHub with the package access_token preference)
        tbl.column('forge_type', size=':10', name_long='!![en]Forge Type',
                   values='github:GitHub,forgejo:Forgejo')
        tbl.column('api_url', name_long='!![en]API URL')  # e.g. https://hub.genro.com/api/v1
        tbl.column('access_token', name_long='!![en]Access Token')

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
        forge_type = self.readColumns(pkey=pkey, columns='$forge_type') if pkey else None
        if forge_type == 'forgejo':
            return self.importForgejoOrganization(org_data, pkey=pkey)

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

    def importForgejoOrganization(self, org_data, pkey):
        """Update an existing Forgejo organization from the Forgejo API payload.

        Forgejo names the fields differently from GitHub (username, full_name,
        created) and has no html_url. The organization is not imported as
        gh_user: Forgejo ids would collide with GitHub user ids.

        Args:
            org_data: dict from Forgejo API /orgs/{org}
            pkey: existing record pkey (Forgejo organizations are created by hand)

        Returns:
            The pkey of the updated record
        """
        with self.recordToUpdate(pkey=pkey) as rec:
            web_url = rec['api_url'].split('/api/')[0]
            rec['github_id'] = org_data['id']
            rec['login'] = org_data['username']
            rec['name'] = org_data.get('full_name')
            rec['html_url'] = f"{web_url}/{org_data['username']}"
            rec['avatar_url'] = org_data.get('avatar_url')
            rec['github_created_at'] = org_data.get('created')
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

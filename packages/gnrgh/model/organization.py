# encoding: utf-8
from gnr.core.gnrbag import Bag

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('organization', pkey='id', name_long='!![en]Organization',
                        name_plural='!![en]Organizations', caption_field='login')
        self.sysFields(tbl)

        # Identity on its git server: github_id is unique within the git_host
        tbl.column('git_host_id', size='22', group='_', name_long='!![en]Git Host',
                   validate_notnull=True).relation(
            'git_host.id', relation_name='organizations',
            mode='foreignkey', onDelete='raise')
        tbl.column('github_id', dtype='L', name_long='!![en]GitHub ID', indexed=True)
        tbl.compositeColumn('host_github_id', columns='git_host_id,github_id', unique=True)
        tbl.column('login', name_long='!![en]Login name', validate_notnull=True)
        tbl.compositeColumn('host_login', columns='git_host_id,login', unique=True)
        tbl.aliasColumn('forge_type', '@git_host_id.type', name_long='!![en]Forge Type')
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

        # Inactive: webhook events are stored but not processed, full sync skips it
        tbl.column('inactive', dtype='B', indexed=True, name_long='!![en]Inactive')

        # Computed
        tbl.formulaColumn('num_repositories', select=dict(table='gnrgh.repository', columns='COUNT(*)',
                                                          where='$organization_id=#THIS.id'),
                          dtype='L', name_long='!![en]Num repositories')

    def importOrganization(self, org_data, pkey=None, git_host_id=None):
        """Import or update an organization from its git server payload.

        Args:
            org_data: dict from the API
            pkey: optional existing record pkey
            git_host_id: the server of org_data (required without pkey)

        Returns:
            The pkey of the imported/updated record
        """
        github_id = org_data['id']
        if pkey:
            git_host_id = self.readColumns(pkey=pkey, columns='$git_host_id')
        else:
            pkey = self.pkeyFromExternal(git_host_id, github_id)
        if self.db.table('gnrgh.git_host').readColumns(pkey=git_host_id, columns='$type') == 'forgejo':
            org_data = self.forgejoOrganizationAsGithub(org_data, git_host_id)

        # Import org as gh_user (type=Organization)
        user_tbl = self.db.table('gnrgh.gh_user')
        org_user_id = user_tbl.importUser(org_data, git_host_id=git_host_id)

        kw = dict(pkey=pkey) if pkey else dict(git_host_id=git_host_id, github_id=github_id,
                                               insertMissing=True)
        with self.recordToUpdate(**kw) as rec:
            rec['git_host_id'] = git_host_id
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

    def forgejoOrganizationAsGithub(self, org_data, git_host_id):
        """Translate a Forgejo /orgs/{org} payload into the GitHub field names.

        Forgejo names the fields differently (username, full_name, created)
        and has no html_url. A payload that already carries `login` (a webhook
        `organization` object) is returned unchanged.

        Args:
            org_data: dict from Forgejo API
            git_host_id: the Forgejo server, for the web url

        Returns:
            A new dict with GitHub field names
        """
        if 'login' in org_data:
            return org_data
        web_url = self.db.table('gnrgh.git_host').webUrl(git_host_id)
        data = dict(org_data)
        data['login'] = org_data['username']
        data['name'] = org_data.get('full_name')
        data['html_url'] = f"{web_url}/{org_data['username']}"
        data['created_at'] = org_data.get('created')
        data['type'] = 'Organization'
        return data

    def processEvent(self, payload, action=None, git_host_id=None):
        """Process a webhook event for organizations.

        Args:
            payload: Complete webhook payload dict
            action: Action type
            git_host_id: the server that sent the event

        Returns:
            The pkey of the created/updated organization, or None if not processed
        """
        org_data = payload.get('organization')
        if not org_data:
            return None

        # Import/update the organization
        return self.importOrganization(org_data, git_host_id=git_host_id)

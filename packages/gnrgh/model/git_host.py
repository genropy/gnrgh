# encoding: utf-8
from gnr.core.gnrdecorator import metadata

GITHUB_API_URL = 'https://api.github.com'


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('git_host', pkey='id', name_long='!![en]Git Host',
                        name_plural='!![en]Git Hosts', caption_field='description',
                        lookup=True)
        self.sysFields(tbl)

        tbl.column('description', name_long='!![en]Description', validate_notnull=True)
        tbl.column('url', unique=True, name_long='!![en]API URL',
                   validate_notnull=True)  # e.g. https://hub.genro.com/api/v1
        tbl.column('type', size=':10', name_long='!![en]Type', validate_notnull=True,
                   values='github:GitHub,forgejo:Forgejo')
        tbl.column('token', name_long='!![en]Token')

    @metadata(mandatory=True)
    def sysRecord_GITHUB(self):
        # the token is filled by the package preference during the upgrade
        # and by hand afterwards
        return self.newrecord(description='GitHub', url=GITHUB_API_URL, type='github')

    def githubHost(self):
        """Return the pkey of the github.com host, used when no organization is given."""
        return self.sysRecord('GITHUB')['id']

    def getClient(self, git_host_id):
        """Return a GithubClient for the host.

        A host without token falls back to the local gh CLI token
        (GithubClient.get_local_gh_token).
        """
        from gnrpkg.gnrgh.github_client import GithubClient
        url, token = self.readColumns(pkey=git_host_id, columns='$url,$token')
        return GithubClient(access_token=token or None, api_url=url)

    def webUrl(self, git_host_id):
        """Return the web base of the host: the API url without its /api/... suffix."""
        url = self.readColumns(pkey=git_host_id, columns='$url')
        if url == GITHUB_API_URL:
            return 'https://github.com'
        return url.split('/api/')[0]

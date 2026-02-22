#!/usr/bin/env python
# encoding: utf-8
from gnr.app.gnrdbo import GnrDboTable, GnrDboPackage

class Package(GnrDboPackage):
    def config_attributes(self):
        return dict(comment='gnrgh package', sqlschema='gnrgh', sqlprefix=True,
                    name_short='GitHub', name_long='GitHub', name_full='GitHub')

    def config_db(self, pkg):
        pass

    def getGithubClient(self):
        """Create and return a GithubClient instance.

        Uses the access_token from package preferences if available,
        otherwise falls back to local gh CLI token.

        Returns:
            GithubClient instance
        """
        from gnrpkg.gnrgh.github_client import GithubClient
        access_token = self.db.application.getPreference('access_token', pkg='gnrgh')
        return GithubClient(access_token=access_token or None)

class Table(GnrDboTable):
    pass

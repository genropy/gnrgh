#!/usr/bin/env python
# encoding: utf-8
import os
from gnr.app.gnrdbo import GnrDboTable, GnrDboPackage

class Package(GnrDboPackage):
    def config_attributes(self):
        return dict(comment='gnrgh package', sqlschema='gnrgh', sqlprefix=True,
                    name_short='gnrgh', name_long='!![en]GitHub Integration', name_full='!![en]GitHub Integration for GenroPy')

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

    def getGitLocal(self):
        """Create and return a GitLocal instance for managing local clones.

        Uses clone_base_path from package preferences if available,
        otherwise defaults to ~/.gnrgh/clones.

        Returns:
            GitLocal instance
        """
        from gnrpkg.gnrgh.git_local import GitLocal
        clone_base_path = self.db.application.getPreference('clone_base_path', pkg='gnrgh')
        if not clone_base_path:
            clone_base_path = os.path.join(os.path.expanduser('~'), '.gnrgh', 'clones')
        os.makedirs(clone_base_path, exist_ok=True)
        return GitLocal(clone_base_path=clone_base_path)

    def getGitHandler(self):
        """Create and return a GitHandler instance for git operations."""
        from gnrpkg.gnrgh.git_handler import GitHandler
        return GitHandler(db=self.db)

class Table(GnrDboTable):
    pass

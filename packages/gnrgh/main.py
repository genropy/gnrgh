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

    def getGithubClient(self, organization_id=None):
        """Create and return a GithubClient for the git_host of an organization.

        Without organization_id the client talks to github.com
        (git_host.githubHost).

        Args:
            organization_id: optional gnrgh.organization pkey

        Returns:
            GithubClient instance
        """
        git_host_tbl = self.db.table('gnrgh.git_host')
        if organization_id:
            git_host_id = self.db.table('gnrgh.organization').readColumns(
                pkey=organization_id, columns='$git_host_id')
        else:
            git_host_id = git_host_tbl.githubHost()
        return git_host_tbl.getClient(git_host_id)

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
    def pkeyFromExternal(self, git_host_id, github_id):
        """Resolve the id a git server gave to an object into the pkey of its row.

        The server id (github_id) is unique only within its git_host: the pair
        is the identity of an imported row at the border (import, sync,
        webhook). Inside gnrgh only the pkey is used.

        Returns:
            The pkey, or None when the pair has no row
        """
        if not git_host_id or github_id is None:
            return None
        rows = self.query(where='$git_host_id=:h AND $github_id=:g',
                          h=git_host_id, g=github_id, columns='$id').fetch()
        return rows[0]['id'] if rows else None

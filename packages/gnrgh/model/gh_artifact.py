# encoding: utf-8
from gnr.core.gnrbag import Bag


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('gh_artifact', pkey='id',
                        name_long='!![en]GitHub Artifact',
                        name_plural='!![en]GitHub Artifacts',
                        caption_field='name')
        self.sysFields(tbl)

        # GitHub unique identifier
        tbl.column('github_id', dtype='L', unique=True, indexed=True,
                   name_long='!![en]GitHub ID')

        # Relations
        tbl.column('organization_id', size='22', group='_',
                   name_long='!![en]Organization').relation(
            'organization.id', relation_name='artifacts',
            mode='foreignkey', onDelete='cascade')

        tbl.column('repository_id', size='22', group='_',
                   name_long='!![en]Repository').relation(
            'repository.id', relation_name='artifacts',
            mode='foreignkey', onDelete='setnull')

        tbl.column('owner_id', size='22', group='_',
                   name_long='!![en]Owner').relation(
            'gh_user.id', relation_name='owned_artifacts',
            mode='foreignkey', onDelete='setnull')

        # Artifact fields
        tbl.column('name', indexed=True, name_long='!![en]Name')
        tbl.column('package_type', size=':16', indexed=True,
                   name_long='!![en]Package Type', name_short='!![en]Type')
        tbl.column('visibility', size=':16', indexed=True,
                   name_long='!![en]Visibility')
        tbl.column('version_count', dtype='L',
                   name_long='!![en]Version Count', name_short='!![en]Versions')

        # URLs
        tbl.column('url', name_long='!![en]API URL')
        tbl.column('html_url', name_long='!![en]Web URL')

        # GitHub timestamps
        tbl.column('github_created_at', dtype='DHZ', indexed=True,
                   name_long='!![en]GitHub Created')
        tbl.column('github_updated_at', dtype='DHZ', indexed=True,
                   name_long='!![en]GitHub Updated')

        # Raw payload from GitHub API
        tbl.column('metadata', dtype='X', name_long='!![en]Metadata')

        # Formula: count actual versions in db
        tbl.formulaColumn('num_versions',
                          select=dict(table='gnrgh.gh_artifact_version',
                                      columns='COUNT(*)',
                                      where='$artifact_id=#THIS.id'),
                          dtype='L', name_long='!![en]Synced Versions')

    def importArtifact(self, artifact_data, organization_id=None, pkey=None):
        """Import or update an artifact from GitHub API payload.

        Args:
            artifact_data: dict from GitHub API
            organization_id: FK to organization (required for new records)
            pkey: optional existing record pkey

        Returns:
            The pkey of the imported/updated record
        """
        github_id = artifact_data['id']
        kw = dict(pkey=pkey) if pkey else dict(github_id=github_id, insertMissing=True)

        # Import owner as gh_user
        owner_id = None
        owner_data = artifact_data.get('owner')
        if owner_data:
            owner_id = self.db.table('gnrgh.gh_user').importUser(owner_data)

        # Find repository_id if repository data present
        repository_id = None
        repo_data = artifact_data.get('repository')
        if repo_data and repo_data.get('id'):
            repo_github_id = repo_data['id']
            repo_rows = self.db.table('gnrgh.repository').query(
                columns='$id',
                where='$github_id=:gid',
                gid=repo_github_id
            ).fetch()
            if repo_rows:
                repository_id = repo_rows[0]['id']

        with self.recordToUpdate(**kw) as rec:
            rec['github_id'] = github_id
            rec['organization_id'] = rec['organization_id'] or organization_id
            rec['repository_id'] = repository_id
            rec['owner_id'] = owner_id
            rec['name'] = artifact_data['name']
            rec['package_type'] = artifact_data['package_type']
            rec['visibility'] = artifact_data.get('visibility')
            rec['version_count'] = artifact_data.get('version_count', 0)
            rec['url'] = artifact_data.get('url')
            rec['html_url'] = artifact_data.get('html_url')
            rec['github_created_at'] = artifact_data.get('created_at')
            rec['github_updated_at'] = artifact_data.get('updated_at')
            rec['metadata'] = Bag(artifact_data)

        return rec['id']

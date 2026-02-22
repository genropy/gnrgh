# encoding: utf-8
from gnr.core.gnrbag import Bag


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('gh_artifact_version', pkey='id',
                        name_long='!![en]Artifact Version',
                        name_plural='!![en]Artifact Versions',
                        caption_field='name')
        self.sysFields(tbl)

        # GitHub unique identifier
        tbl.column('github_id', dtype='L', unique=True, indexed=True,
                   name_long='!![en]GitHub ID')

        # Relation to artifact (cascade delete)
        tbl.column('artifact_id', size='22', group='_',
                   name_long='!![en]Artifact').relation(
            'gh_artifact.id', relation_name='versions',
            mode='foreignkey', onDelete='cascade')

        # Version fields
        tbl.column('name', indexed=True, name_long='!![en]Version Name')
        tbl.column('description', name_long='!![en]Description')
        tbl.column('license', name_long='!![en]License')

        # URLs
        tbl.column('url', name_long='!![en]API URL')
        tbl.column('html_url', name_long='!![en]Web URL')
        tbl.column('artifact_html_url', name_long='!![en]Artifact Web URL')

        # GitHub timestamps
        tbl.column('github_created_at', dtype='DH', indexed=True,
                   name_long='!![en]GitHub Created')
        tbl.column('github_updated_at', dtype='DH', indexed=True,
                   name_long='!![en]GitHub Updated')
        tbl.column('github_deleted_at', dtype='DH',
                   name_long='!![en]GitHub Deleted')

        # Raw payload from GitHub API
        tbl.column('metadata', dtype='X', name_long='!![en]Metadata')

    def importArtifactVersion(self, version_data, artifact_id=None, pkey=None):
        """Import or update an artifact version from GitHub API payload.

        Args:
            version_data: dict from GitHub API
            artifact_id: FK to gh_artifact (required for new records)
            pkey: optional existing record pkey

        Returns:
            The pkey of the imported/updated record
        """
        github_id = version_data['id']
        kw = dict(pkey=pkey) if pkey else dict(github_id=github_id, insertMissing=True)

        with self.recordToUpdate(**kw) as rec:
            rec['github_id'] = github_id
            rec['artifact_id'] = rec['artifact_id'] or artifact_id
            rec['name'] = version_data['name']
            rec['description'] = version_data.get('description')
            rec['license'] = version_data.get('license')
            rec['url'] = version_data.get('url')
            rec['html_url'] = version_data.get('html_url')
            rec['artifact_html_url'] = version_data.get('package_html_url')
            rec['github_created_at'] = version_data.get('created_at')
            rec['github_updated_at'] = version_data.get('updated_at')
            rec['github_deleted_at'] = version_data.get('deleted_at')
            rec['metadata'] = Bag(version_data)

        return rec['id']

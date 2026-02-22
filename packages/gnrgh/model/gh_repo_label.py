# encoding: utf-8


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('gh_repo_label', pkey='id',
                        name_long='!![en]Repository Label',
                        name_plural='!![en]Repository Labels',
                        caption_field='name')
        self.sysFields(tbl)

        # GitHub unique identifier
        tbl.column('github_id', dtype='L', unique=True, indexed=True,
                   name_long='!![en]GitHub ID')

        # Repository relation
        tbl.column('repository_id', size='22', group='_',
                   name_long='!![en]Repository').relation(
            'repository.id', relation_name='labels',
            mode='foreignkey', onDelete='cascade')

        # Label fields
        tbl.column('name', name_long='!![en]Name')
        tbl.column('color', size=':10', name_long='!![en]Color')
        tbl.column('description', name_long='!![en]Description')

        # Composite unique key
        tbl.compositeColumn('repo_label', columns='repository_id,name', unique=True)

    def importLabel(self, label_data, repository_id):
        """Import or update a label from GitHub API payload.

        Args:
            label_data: dict from GitHub API
            repository_id: FK to repository

        Returns:
            The pkey of the imported/updated record
        """
        github_id = label_data['id']

        with self.recordToUpdate(github_id=github_id, insertMissing=True) as rec:
            rec['github_id'] = github_id
            rec['repository_id'] = repository_id
            rec['name'] = label_data['name']
            rec['color'] = label_data.get('color')
            rec['description'] = label_data.get('description')

        return rec['id']

    def syncLabels(self, labels_data, repository_id):
        """Sync labels for a repository.

        Adds new labels and removes old ones not in the list.

        Args:
            labels_data: List of label dicts from GitHub API
            repository_id: FK to repository
        """
        # Get existing labels for this repository
        existing = self.query(
            columns='$id,$github_id',
            where='$repository_id=:repository_id',
            repository_id=repository_id
        ).fetch()

        existing_ids = {row['github_id']: row['id'] for row in existing}
        new_ids = {label['id'] for label in labels_data}

        # Remove labels not in the new list
        for github_id, pkey in existing_ids.items():
            if github_id not in new_ids:
                self.delete({'id': pkey})

        # Add/update labels
        for label_data in labels_data:
            self.importLabel(label_data, repository_id=repository_id)

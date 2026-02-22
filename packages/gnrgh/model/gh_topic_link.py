# encoding: utf-8


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('gh_topic_link', pkey='id',
                        name_long='!![en]GitHub Topic Link',
                        name_plural='!![en]GitHub Topic Links',
                        caption_field='topic_name')
        self.sysFields(tbl)

        # Topic relation
        tbl.column('topic_name', name_long='!![en]Topic').relation(
            'gh_topic.name', relation_name='links',
            mode='foreignkey', onDelete='cascade')

        # Repository relation (topics are only for repositories)
        tbl.column('repository_id', size='22', group='_',
                   name_long='!![en]Repository').relation(
            'repository.id', relation_name='topic_links',
            mode='foreignkey', onDelete='cascade')

        # Composite unique key
        tbl.compositeColumn('topic_repository', columns='topic_name,repository_id', unique=True)

    def importTopicLink(self, topic_name, repository_id):
        """Import or update a topic link for a repository.

        Args:
            topic_name: Topic name string
            repository_id: FK to repository

        Returns:
            The pkey of the imported/updated record
        """
        # Ensure topic exists
        self.db.table('gnrgh.gh_topic').touchTopic(topic_name)

        with self.recordToUpdate(topic_name=topic_name, repository_id=repository_id,
                                 insertMissing=True) as rec:
            pass  # Just create/update the link

        return rec['id']

    def syncTopics(self, topics, repository_id):
        """Sync topics for a repository.

        Adds new topics and removes old ones not in the list.

        Args:
            topics: List of topic name strings
            repository_id: FK to repository
        """
        # Get existing topics for this repository
        existing = self.query(
            columns='$id,$topic_name',
            where='$repository_id=:repository_id',
            repository_id=repository_id
        ).fetch()

        existing_topics = {row['topic_name']: row['id'] for row in existing}
        new_topics = set(topics)

        # Remove topics not in the new list
        for topic_name, topic_id in existing_topics.items():
            if topic_name not in new_topics:
                self.delete({'id': topic_id})

        # Add new topics
        for topic_name in new_topics:
            if topic_name not in existing_topics:
                self.importTopicLink(topic_name, repository_id=repository_id)

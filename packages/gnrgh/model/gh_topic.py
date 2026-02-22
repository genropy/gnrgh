# encoding: utf-8


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('gh_topic', pkey='name',
                        name_long='!![en]GitHub Topic',
                        name_plural='!![en]GitHub Topics',
                        caption_field='name', lookup=True)
        self.sysFields(tbl, id=False)

        # Topic name is the primary key
        tbl.column('name', name_long='!![en]Topic Name')

    def touchTopic(self, name):
        """Ensure a topic exists, create if missing.

        Args:
            name: Topic name

        Returns:
            The topic name (pkey)
        """
        with self.recordToUpdate(pkey=name, insertMissing=True) as rec:
            rec['name'] = name

        return name

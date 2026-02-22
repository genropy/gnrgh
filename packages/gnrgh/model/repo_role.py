# encoding: utf-8

from gnr.core.gnrdecorator import metadata

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('repo_role', pkey='code',
                        name_long='!![en]Repository Role',
                        name_plural='!![en]Repository Roles',
                        caption_field='name',
                        lookup=True)
        self.sysFields(tbl, id=False)
        tbl.column('code', size=':32', name_long='!![en]Code')
        tbl.column('name', name_long='!![en]Name')
        tbl.column('repo_level', size=':16', name_long='!![en]Repository Level',
                   values='read,triage,push,maintain,admin')

    @metadata(mandatory=True)
    def sysRecord_OWNER(self):
        return self.newrecord(code='OWNER', name='Owner', repo_level='admin', reserved=True)

    @metadata(mandatory=True)
    def sysRecord_VICEMAINTAINER(self):
        return self.newrecord(code='VICEMAINTAINER(', name='Vice Maintainer', repo_level='maintain', reserved=True)

    @metadata(mandatory=True)
    def sysRecord_MAINTAINER(self):
        return self.newrecord(code='MAINTAINER', name='Maintainer', repo_level='maintain', reserved=True)

    @metadata(mandatory=True)
    def sysRecord_CONTRIBUTOR(self):
        return self.newrecord(code='CONTRIBUTOR', name='Contributor', repo_level='triage', reserved=True)

    @metadata(mandatory=True)
    def sysRecord_EXTERNAL(self):
        return self.newrecord(code='EXTERNAL', name='External', repo_level='read', reserved=True)

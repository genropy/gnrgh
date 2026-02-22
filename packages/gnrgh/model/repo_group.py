# encoding: utf-8

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('repo_group', pkey='code',
                        name_long='!![en]Repository Group',
                        name_plural='!![en]Repository Groups',
                        caption_field='name',
                        lookup=True)
        self.sysFields(tbl, id=False)
        tbl.column('code', size=':32', name_long='!![en]Code')
        tbl.column('name', name_long='!![en]Name')
        tbl.column('description', name_long='!![en]Description')
        tbl.column('color', name_long='!![en]Color')
        tbl.column('organization_id',size='22', group='_', name_long=''
                    ).relation('organization.id', relation_name='repo_groups', 
                               mode='foreignkey', onDelete='cascade')
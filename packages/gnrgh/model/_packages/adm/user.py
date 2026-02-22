# encoding: utf-8

class Table(object):
    def config_db(self,pkg):
        tbl=pkg.table('user')
        tbl.column('gh_user_id',size='22', group='_', name_long='!![en]GitHub user',plugToForm=True
                    ).relation('gnrgh.gh_user.id', one_one=True,
                               relation_name='adm_user',
                               mode='foreignkey',
                               onDelete='setnull')
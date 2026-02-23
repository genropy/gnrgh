# encoding: utf-8


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('branch_commit', pkey='id',
                        name_long='!![en]Branch Commit',
                        name_plural='!![en]Branch Commits')
        self.sysFields(tbl)

        tbl.column('branch_id', size='22', group='_',
                   name_long='!![en]Branch').relation(
            'branch.id', relation_name='branch_commits',
            mode='foreignkey', onDelete='cascade')

        tbl.column('commit_id', size='22', group='_',
                   name_long='!![en]Commit').relation(
            'commit.id', relation_name='branch_commits',
            mode='foreignkey', onDelete='cascade')

        tbl.compositeColumn('branch_commit_unique',
                           columns='branch_id,commit_id', unique=True)

    def linkBranchCommit(self, branch_id=None, commit_id=None):
        with self.recordToUpdate(branch_id=branch_id, commit_id=commit_id,
                                 insertMissing=True) as rec:
            rec['branch_id'] = branch_id
            rec['commit_id'] = commit_id
        return rec['id']

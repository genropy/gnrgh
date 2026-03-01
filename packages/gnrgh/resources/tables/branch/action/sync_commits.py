# -*- coding: utf-8 -*-

from datetime import datetime
from gnr.web.batch.btcaction import BaseResourceAction

caption = 'Sync Commits'
description = 'Import commits from GitHub for selected branches'

class Main(BaseResourceAction):
    batch_prefix = 'SYNC_COMMITS'
    batch_title = caption
    batch_selection_savedQuery = False

    def do(self):
        pkeys = self.get_selection_pkeys()
        if not pkeys:
            return
        rows = self.tblobj.query(
            where='$id IN :pkeys',
            pkeys=pkeys,
            columns='$id,$name,$repository_id,$last_sync_ts,$repo_full_name'
        ).fetch()
        github_service = self.db.package('gnrgh').getGithubClient()
        commit_tbl = self.db.table('gnrgh.commit')

        for row in self.btc.thermo_wrapper(rows, line_code='branches',
                                           message='!![en]Branches'):
            full_name = row['repo_full_name']
            if not full_name or '/' not in full_name:
                continue
            owner, repo_name = full_name.split('/', 1)
            kw = {}
            if row['last_sync_ts']:
                kw['since'] = row['last_sync_ts'].isoformat()
            commits_data = github_service.getCommits(
                owner=owner, repo=repo_name,
                sha=row['name'], per_page=100,
                paginate=True, **kw
            )
            commit_tbl.importCommits(commits_data,
                                     repository_id=row['repository_id'],
                                     branch_id=row['id'])
            with self.tblobj.recordToUpdate(pkey=row['id']) as rec:
                rec['last_sync_ts'] = datetime.utcnow()
            self.db.commit()

    batch_dialog_width = '400px'

    def table_script_parameters_pane(self, pane, record_count=None, **kwargs):
        pane.div('Sync commits for <b>%s</b> selected branches.' % (record_count or 0),
                 style='margin:10px;padding:10px;background:#fff3cd;border-radius:4px;'
                        'word-wrap:break-word;')

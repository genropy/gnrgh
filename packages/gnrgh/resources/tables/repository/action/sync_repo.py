# -*- coding: utf-8 -*-

from gnr.web.batch.btcaction import BaseResourceAction

caption = 'Sync Repo'
description = 'Sync branches, commits, issues, PRs, topics, labels from GitHub'

class Main(BaseResourceAction):
    batch_prefix = 'SYNC_REPO'
    batch_title = caption
    batch_thermo_lines = 'repos,import_type,detail'
    batch_selection_savedQuery = False

    def do(self):
        pkeys = self.get_selection_pkeys()
        self.tblobj.syncRepo(pkeys=pkeys, thermo_cb=self.btc.thermo_wrapper)

    batch_dialog_width = '400px'

    def table_script_parameters_pane(self, pane, record_count=None, **kwargs):
        pane.div('Sync <b>%s</b> selected repositories.' % (record_count or 0),
                 style='margin:10px;padding:10px;background:#fff3cd;border-radius:4px;'
                        'word-wrap:break-word;')
        pane.div('Will import: branches, commits, issues, pull requests, topics, labels, collaborators.',
                 style='margin:10px;font-size:12px;color:#666;')

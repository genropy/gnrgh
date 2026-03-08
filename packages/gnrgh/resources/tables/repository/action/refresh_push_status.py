# -*- coding: utf-8 -*-

"""Refresh push status from GitHub API.

Fetches the latest pushed_at timestamp and metadata from GitHub
for all repositories in every configured organization.
Updates sync status indicators in the repository grid.
"""

from gnr.web.batch.btcaction import BaseResourceAction

caption = 'Refresh Push Status'
description = 'Fetch pushed_at from GitHub API for all repositories and update sync status'

class Main(BaseResourceAction):
    batch_prefix = 'REFRESH_PUSH'
    batch_title = caption
    batch_thermo_lines = 'orgs,repos'
    batch_selection_savedQuery = False
    batch_cancellable = True

    def do(self):
        self.tblobj.refreshPushStatus(thermo_cb=self.btc.thermo_wrapper)

    batch_dialog_width = '400px'

    def table_script_parameters_pane(self, pane, **kwargs):
        pane.div('!![en]Fetch latest <b>pushed_at</b> from GitHub for all organizations.',
                 style='margin:10px;padding:10px;background:#d4edda;border-radius:4px;'
                        'max-width:350px;')
        pane.div('!![en]Updates sync status indicators (green/red) in the grid.',
                 style='margin:10px;font-size:12px;color:#666;max-width:350px;')

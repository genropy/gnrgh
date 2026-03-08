# -*- coding: utf-8 -*-

"""Check repositories status.

Syncs repository list from GitHub API, updates pushed_at timestamps,
and verifies local clone status for all configured organizations.
"""

from gnr.web.batch.btcaction import BaseResourceAction

caption = 'Check Repo'
description = 'Sync repos from GitHub, update pushed_at, verify local clones'

class Main(BaseResourceAction):
    batch_prefix = 'CHECK_REPO'
    batch_title = caption
    batch_thermo_lines = 'orgs,repos'
    batch_schedulable = True
    batch_selection_savedQuery = False

    def do(self):
        self.tblobj.checkRepo(thermo_cb=self.btc.thermo_wrapper)

    def table_script_parameters_pane(self, pane, **kwargs):
        pane.div("""!![en]Sync repositories from GitHub, update pushed_at, and verify local clone status.""",
                 style='margin:10px;padding:10px;background:#fff3cd;border-radius:4px;'
                        'font-size:12px;word-wrap:break-word;max-width:350px;')

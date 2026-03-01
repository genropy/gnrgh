# -*- coding: utf-8 -*-

from gnr.web.batch.btcaction import BaseResourceAction

caption = 'Refresh Clone Status'
description = 'Check filesystem and update clone tracking fields for selected repositories'
tags = '_DEV_'

class Main(BaseResourceAction):
    batch_prefix = 'REFRESH_CLONE'
    batch_title = caption
    batch_selection_savedQuery = False

    def do(self):
        pkeys = self.get_selection_pkeys()
        if not pkeys:
            return
        repo_tbl = self.tblobj
        for pkey in self.btc.thermo_wrapper(pkeys, line_code='repos', message='!![en]Repositories'):
            repo_tbl.refreshCloneStatus(pkey)
            self.db.commit()

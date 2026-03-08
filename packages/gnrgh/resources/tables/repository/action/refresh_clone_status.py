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
        from gnrpkg.gnrgh.lib.git_handler import GitHandler
        handler = GitHandler(self.db)
        pkeys = self.get_selection_pkeys()
        if not pkeys:
            return
        for pkey in self.btc.thermo_wrapper(pkeys, line_code='repos',
                                            message='!![en]Repositories'):
            handler.refresh_clone_status(pkey)
            self.db.commit()

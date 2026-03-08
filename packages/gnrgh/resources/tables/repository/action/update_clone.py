# -*- coding: utf-8 -*-

from gnr.web.batch.btcaction import BaseResourceAction

caption = 'Update Clone'
description = 'Clone or pull selected repositories'

class Main(BaseResourceAction):
    batch_prefix = 'UPD_CLONE'
    batch_title = caption
    batch_thermo_lines = 'repos'
    batch_selection_savedQuery = False

    def do(self):
        pkeys = self.get_selection_pkeys()
        self.tblobj.updateClone(pkeys=pkeys, thermo_cb=self.btc.thermo_wrapper)

    def table_script_parameters_pane(self, pane, record_count=None, **kwargs):
        pane.div('Clone or pull <b>%s</b> selected repositories.' % (record_count or 0),
                 style='margin:10px;padding:10px;background:#fff3cd;border-radius:4px;'
                        'font-size:12px;word-wrap:break-word;')

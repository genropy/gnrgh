# -*- coding: utf-8 -*-

from gnr.web.batch.btcaction import BaseResourceAction

caption = 'Clone / Pull Selected'
description = 'Clone or pull selected repositories'

class Main(BaseResourceAction):
    batch_prefix = 'PULL_ALL'
    batch_title = caption
    batch_selection_savedQuery = False

    def do(self):
        pkeys = self.get_selection_pkeys()
        if not pkeys:
            return
        repo_tbl = self.tblobj
        rows = repo_tbl.query(
            where='$id IN :pkeys',
            pkeys=pkeys,
            columns='$id,$full_name,$clone_path'
        ).fetch()
        for row in self.btc.thermo_wrapper(rows, line_code='repos', message='!![en]Clone / Pull'):
            try:
                if row['clone_path']:
                    repo_tbl.pullRepository(row['id'])
                else:
                    repo_tbl.cloneRepository(row['id'])
                self.db.commit()
            except Exception:
                self.db.rollback()

    def table_script_parameters_pane(self, pane, **kwargs):
        pane.div("""!![en]Clone repositories that are not yet cloned, pull latest changes for already cloned ones.""",
                 style='margin:10px;padding:10px;background:#fff3cd;border-radius:4px;'
                        'font-size:12px;word-wrap:break-word;')

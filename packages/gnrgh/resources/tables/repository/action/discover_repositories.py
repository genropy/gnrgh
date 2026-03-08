# -*- coding: utf-8 -*-

"""Discover repositories from GitHub organizations.

Queries the GitHub API for each configured organization and creates
or updates the corresponding repository records in the local database.
This is typically the first action to run when setting up a new
organization or when new repositories have been created on GitHub.
"""

from gnr.web.batch.btcaction import BaseResourceAction

caption = 'Discover Repositories'
description = 'Discover repositories from GitHub organizations and create or update local records'

class Main(BaseResourceAction):
    batch_prefix = 'DISC_REPO'
    batch_title = caption
    batch_thermo_lines = 'orgs,repos'
    batch_schedulable = True
    batch_selection_savedQuery = False

    def do(self):
        self.tblobj.discoverRepositories(thermo_cb=self.btc.thermo_wrapper)

    def table_script_parameters_pane(self, pane, **kwargs):
        pane.div("""!![en]Discover repositories from all configured GitHub organizations and create or update local records.""",
                 style='margin:10px;padding:10px;background:#fff3cd;border-radius:4px;'
                        'font-size:12px;word-wrap:break-word;max-width:350px;')

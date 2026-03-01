# -*- coding: utf-8 -*-

from gnr.web.batch.btcaction import BaseResourceAction

caption = 'Update Repo List'
description = 'Fetch repository list from all GitHub organizations and update local records'

class Main(BaseResourceAction):
    batch_prefix = 'IMP_REPO'
    batch_title = caption
    batch_schedulable = True
    batch_selection_savedQuery = False

    def do(self):
        service = self.db.package('gnrgh').getGithubClient()
        orgs = self.db.table('gnrgh.organization').query(
            columns='$id,$login',
            order_by='$login'
        ).fetch()

        for org_row in self.btc.thermo_wrapper(orgs, line_code='orgs', message='!![en]Organizations'):
            org_login = org_row['login']
            organization_id = org_row['id']
            repos = service.getRepositories(organization=org_login)
            for repo_data in self.btc.thermo_wrapper(repos, line_code='repos', message='!![en]Repositories'):
                self.tblobj.importRepository(repo_data, organization_id=organization_id)
                self.db.commit()

    def table_script_parameters_pane(self, pane, **kwargs):
        pane.div("""!![en]Fetch repository list from all organizations and create or update local records.""",
                 style='margin:10px;padding:10px;background:#fff3cd;border-radius:4px;'
                        'font-size:12px;word-wrap:break-word;')

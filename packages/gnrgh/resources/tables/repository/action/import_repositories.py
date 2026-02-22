# -*- coding: utf-8 -*-

from gnr.web.batch.btcaction import BaseResourceAction

caption = 'Import Repositories'
description = 'Import repositories, branches and latest commits from organizations'

class Main(BaseResourceAction):
    batch_prefix = 'IMP_REPO'
    batch_title = caption
    batch_schedulable = True

    def do(self):
        service = self.db.package('gnrgh').getGithubClient()
        organizations_pkeys = self.batch_parameters['organizations_pkeys']
        if not organizations_pkeys:
            return
        organizations_pkeys = organizations_pkeys.split(',')
        orgs = self.db.table('gnrgh.organization').query(
            columns='$id,$login',
            where='$id IN :organizations_pkeys',
            organizations_pkeys=organizations_pkeys
        ).fetch()

        branch_tbl = self.db.table('gnrgh.branch')
        commit_tbl = self.db.table('gnrgh.commit')

        for org_row in self.btc.thermo_wrapper(orgs, line_code='orgs', message='!![en]Organizations'):
            org_login = org_row['login']
            organization_id = org_row['id']
            repos = service.getRepositories(organization=org_login)
            for repo_data in self.btc.thermo_wrapper(repos, line_code='repos', message='!![en]Repositories'):
                repository_id = self.tblobj.importRepository(repo_data, organization_id=organization_id)
                full_name = repo_data.get('full_name', '')
                if not full_name or '/' not in full_name:
                    self.db.commit()
                    continue
                owner, repo_name = full_name.split('/', 1)

                # Import branches
                branches_data = service.getBranches(owner=owner, repo=repo_name)
                branch_tbl.importBranches(branches_data, repository_id=repository_id)

                # Import last 5 commits for each branch
                branches = branch_tbl.query(
                    where='$repository_id=:repo_id',
                    repo_id=repository_id,
                    columns='$id,$name'
                ).fetch()
                for br in self.btc.thermo_wrapper(branches, line_code='detail', message='!![en]Branches'):
                    commits_data = service.getCommits(
                        owner=owner, repo=repo_name,
                        sha=br['name'], per_page=5, paginate=False
                    )
                    commit_tbl.importCommits(commits_data, branch_id=br['id'])

                self.db.commit()

    def table_script_parameters_pane(self, pane, **kwargs):
        pane.div("""!![en]Import or update repositories from selected organizations.
For each repository: creates a new record or updates the existing one,
imports all branches, and fetches the last 5 commits per branch.""",
                 style='margin:10px;padding:10px;background:#fff3cd;border-radius:4px;'
                        'font-size:12px;word-wrap:break-word;')
        fb = pane.formbuilder()
        fb.checkboxtext(value='^.organizations_pkeys', lbl='!!Organizations',
                        table='gnrgh.organization',
                        popup=True, cols=1)

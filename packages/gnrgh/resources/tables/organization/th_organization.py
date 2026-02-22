#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method

class View(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.cell('avatar', calculated=True, width='3em', name=' ',
               _customGetter="function(row){var url=row.avatar_url; return url ? '<img src=\"'+url+'\" style=\"width:24px;height:24px;border-radius:50%\">' : '';}")
        r.fieldcell('login')
        r.fieldcell('name', width='15em')
        r.fieldcell('github_id', width='8em')
        r.fieldcell('num_repositories', name='# Repos', width='6em')
        r.fieldcell('github_created_at', width='10em')
        r.fieldcell('github_updated_at', width='10em')
        r.fieldcell('commit_policy', width='6em')
        r.fieldcell('html_url', width='15em')

    def th_order(self):
        return 'login'

    def th_query(self):
        return dict(column='login', op='contains', val='')


class Form(BaseComponent):

    def th_form(self, form):
        bc = form.center.borderContainer()
        self.organizationHeader(bc.contentPane(region='top', datapath='.record', padding='10px'))
        tc = bc.tabContainer(region='center')
        self.organizationRepositories(tc.contentPane(title='!![en]Repositories'))
        self.organizationArtifacts(tc.contentPane(title='!![en]Artifacts'))
        self.organizationMembers(tc.contentPane(title='!![en]Members'))
        self.organizationEvents(tc.contentPane(title='!![en]Events'))

    def th_top_custom(self, top):
        bar = top.bar.replaceSlots('right_placeholder', 'syncbtn,right_placeholder')
        btn = bar.syncbtn.slotButton('!![en]Update from GitHub')
        btn.dataRpc(self.rpc_org_update,
                    organization_id='=#FORM.record.id',
                    _lockScreen=True,
                    _onResult='this.form.reload();')

    def organizationHeader(self, pane):
        box = pane.div(display='flex', align_items='flex-start')
        box.img(src='^.avatar_url', height='64px', width='64px',
                style='border-radius:50%;margin-right:15px;margin-top:5px;')
        fb = box.formlet(cols=4)
        fb.field('login')
        fb.field('name')
        fb.field('github_id', readonly=True)
        fb.field('commit_policy')
        fb.field('html_url', colspan=2)
        fb.field('github_created_at', readonly=True)
        fb.field('github_updated_at', readonly=True)

    def organizationRepositories(self, pane):
        th = pane.dialogTableHandler(relation='@repositories', batchAssign=True,
                                     viewResource='ViewFromOrganization',
                                     addrow=False, delrow=False,
                                     margin='2px', border='1px solid silver', rounded=4)
        th.view.top.bar.replaceSlots('#', '#,syncBtn')
        bar = th.view.top.bar
        # Normal sync button
        btn = bar.syncBtn.slotButton('!![en]Update from GitHub')
        btn.dataRpc(self.rpc_org_syncRepositories,
                    organization_id='=#FORM.record.id',
                    _lockScreen=True,
                    _onResult='this.form.reload();')

    def organizationArtifacts(self, pane):
        th = pane.dialogTableHandler(relation='@artifacts',
                                     viewResource='ViewFromOrganization',
                                     addrow=False, delrow=False,
                                     margin='2px', border='1px solid silver', rounded=4)
        th.view.top.bar.replaceSlots('#', '#,syncBtn')
        btn = th.view.top.bar.syncBtn.slotButton('!![en]Update from GitHub')
        btn.dataRpc(self.rpc_org_syncArtifacts,
                    organization_id='=#FORM.record.id',
                    _lockScreen=True,
                    _onResult='this.form.reload();')

    def organizationMembers(self, pane):
        th = pane.dialogTableHandler(relation='@user_connections',
                                     viewResource='ViewMembers',
                                     margin='2px', border='1px solid silver', rounded=4)
        th.view.top.bar.replaceSlots('#', '#,createUsersBtn,syncBtn')
        bar = th.view.top.bar
        # Create ADM users button
        createUsersBtn = bar.createUsersBtn.slotButton('!![en]Create ADM Users',
                                                        disabled='^.grid.currentSelectedPkeys?=!#v || #v.length===0')
        createUsersBtn.dataRpc(self.rpc_createAdmUsersFromMembers,
                               connection_pkeys='=.grid.currentSelectedPkeys',
                               _lockScreen=True,
                               _onResult='FIRE .grid.reload;')
        # Sync button
        btn = bar.syncBtn.slotButton('!![en]Update from GitHub')
        btn.dataRpc(self.rpc_org_syncMembers,
                    organization_id='=#FORM.record.id',
                    _lockScreen=True,
                    _onResult='this.form.reload();')

    def organizationEvents(self, pane):
        th = pane.plainTableHandler(relation='@source_events',
                                     viewResource='ViewFromOrganization',
                                     margin='2px', border='1px solid silver',
                                     rounded=4)

    @public_method
    def rpc_org_update(self, organization_id=None):
        """Update organization and all dependencies from GitHub."""
        tbl = self.db.table('gnrgh.organization')
        login = tbl.readColumns(pkey=organization_id, columns='$login')
        github_service = self.db.package('gnrgh').getGithubClient()

        # Update organization
        org_data = github_service.getOrganization(organization=login)
        if org_data:
            tbl.importOrganization(org_data, pkey=organization_id)

        # Sync repositories
        repos = github_service.getRepositories(organization=login)
        repo_tbl = self.db.table('gnrgh.repository')
        for repo in repos:
            repo_tbl.importRepository(repo, organization_id=organization_id)

        # Sync branches for each repository
        branch_tbl = self.db.table('gnrgh.branch')
        repo_records = repo_tbl.query(
            where='$organization_id=:org_id',
            org_id=organization_id,
            columns='$id,$full_name'
        ).fetch()
        for repo_rec in repo_records:
            full_name = repo_rec['full_name']
            if full_name and '/' in full_name:
                owner, repo_name = full_name.split('/', 1)
                branches_data = github_service.getBranches(owner=owner, repo=repo_name)
                branch_tbl.importBranches(branches_data, repository_id=repo_rec['id'])

        # Sync members
        connection_tbl = self.db.table('gnrgh.gh_user_connection')
        user_tbl = self.db.table('gnrgh.gh_user')
        connection_tbl.syncMembers(
            github_service=github_service,
            user_tbl=user_tbl,
            organization_id=organization_id,
            login=login
        )

        # Sync artifacts
        packages = github_service.getPackages(organization=login)
        artifact_tbl = self.db.table('gnrgh.gh_artifact')
        for pkg in packages:
            artifact_tbl.importArtifact(pkg, organization_id=organization_id)

        self.db.commit()

    @public_method
    def rpc_org_syncMembers(self, organization_id=None):
        """Sync organization members from GitHub."""
        org_tbl = self.db.table('gnrgh.organization')
        login = org_tbl.readColumns(pkey=organization_id, columns='$login')

        github_service = self.db.package('gnrgh').getGithubClient()
        connection_tbl = self.db.table('gnrgh.gh_user_connection')
        user_tbl = self.db.table('gnrgh.gh_user')

        connection_tbl.syncMembers(
            github_service=github_service,
            user_tbl=user_tbl,
            organization_id=organization_id,
            login=login
        )

        self.db.commit()

    @public_method
    def rpc_org_syncRepositories(self, organization_id=None):
        """Sync organization repositories from GitHub."""
        org_tbl = self.db.table('gnrgh.organization')
        login = org_tbl.readColumns(pkey=organization_id, columns='$login')

        github_service = self.db.package('gnrgh').getGithubClient()
        repos = github_service.getRepositories(organization=login)

        repo_tbl = self.db.table('gnrgh.repository')
        for repo in repos:
            repo_tbl.importRepository(repo, organization_id=organization_id)

        self.db.commit()

    @public_method
    def rpc_createAdmUsersFromMembers(self, connection_pkeys=None):
        """Create ADM users from selected GitHub organization members."""
        if not connection_pkeys:
            return

        connection_tbl = self.db.table('gnrgh.gh_user_connection')
        gh_user_tbl = self.db.table('gnrgh.gh_user')
        adm_user_tbl = self.db.table('adm.user')

        created_count = 0
        for connection_id in connection_pkeys:
            # Get gh_user_id from connection
            gh_user_id = connection_tbl.readColumns(pkey=connection_id, columns='$gh_user_id')
            if not gh_user_id:
                continue

            # Get GitHub user login and check if adm_user already exists
            gh_user_data = gh_user_tbl.record(pkey=gh_user_id, columns='$login,$adm_user_id').output('dict')
            if not gh_user_data or gh_user_data.get('adm_user_id'):
                continue

            login = gh_user_data.get('login')
            if not login:
                continue

            # Check if username already exists in adm.user
            existing = adm_user_tbl.query(
                columns='$id',
                where='$username=:username',
                username=login
            ).fetch()

            if existing:
                adm_user_tbl.update(dict(id=existing[0]['id'], gh_user_id=gh_user_id))
                continue

            # Create new adm.user with status='wait' and link to gh_user
            adm_user_tbl.insert(adm_user_tbl.newrecord(
                username=login,
                status='wait',
                gh_user_id=gh_user_id
            ))
            created_count += 1

        self.db.commit()
        return created_count

    @public_method
    def rpc_org_syncArtifacts(self, organization_id=None):
        """Sync organization artifacts from GitHub."""
        org_tbl = self.db.table('gnrgh.organization')
        login = org_tbl.readColumns(pkey=organization_id, columns='$login')

        github_service = self.db.package('gnrgh').getGithubClient()
        packages = github_service.getPackages(organization=login)

        artifact_tbl = self.db.table('gnrgh.gh_artifact')
        for pkg in packages:
            artifact_tbl.importArtifact(pkg, organization_id=organization_id)

        self.db.commit()

    def th_options(self):
        return dict(dialog_parentRatio=.8)

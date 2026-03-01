#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method, customizable

class View(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('full_name', width='18em')
        r.fieldcell('repo_group', width='8em', name='!![en]Group')
        cs = r.columnset('activity', name='!![en]Activity', background='#5b9bd5')
        cs.fieldcell('open_issues_count', width='5em', name='!![en]Issues')
        cs.fieldcell('open_pull_requests_count', width='5em', name='!![en]PRs')
        cs = r.columnset('github', name='!![en]GitHub', background='darkorange')
        cs.fieldcell('sync_status', width='3em', name=' ', semaphore=True)
        cs.fieldcell('pushed_at', width='11em', name='!![en]Last Push',
            _customGetter="""function(row){
                var v=row.pushed_at; if(!v) return '';
                var d=new Date(v);
                if(isNaN(d)) return v;
                var pad=function(n){return n<10?'0'+n:n;};
                return d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate())+' '+pad(d.getHours())+':'+pad(d.getMinutes());
            }""")
        cs.fieldcell('last_sync_ts', width='11em', name='!![en]Last Sync')
        cs = r.columnset('clone', name='!![en]Clone', background='#5b9bd5')
        cs.fieldcell('clone_status', width='3em', name=' ', semaphore=True)
        cs.fieldcell('local_branch', width='8em', name='!![en]Branch')
        cs.fieldcell('last_pull_ts', width='11em', name='!![en]Last Pull')
        r.fieldcell('html_url', name=' ', width='2.5em',
               template='<a href="$html_url" target="_blank"><img src="/_rsrc/common/css_icons/svg/16/link_connected.svg" height="13px"/></a>')

    def th_groupedStruct(self, struct):
        """By last commit date"""
        r = struct.view().rows()
        r.fieldcell('last_commit_ts', name='!![en]Year', width='6em', group_aggr='YYYY')
        r.fieldcell('last_commit_ts', name='!![en]Month', width='8em', group_aggr='YYYY-MM')
        r.cell('_grp_count', name='!![en]Repos', width='5em', group_aggr='sum', dtype='L', childname='_grp_count')
        r.fieldcell('branch_count', width='6em', name='!![en]Branches', dtype='L', group_aggr='sum')
        r.fieldcell('open_issues_count', width='6em', name='!![en]Issues', dtype='L', group_aggr='sum')
        r.fieldcell('open_pull_requests_count', width='6em', name='!![en]PRs', dtype='L', group_aggr='sum')

    def th_order(self):
        return 'name'

    def th_query(self):
        return dict(column='name', op='contains', val='')

    def th_queryBySample(self):
        return dict(fields=[
            dict(field='name', lbl='!![en]Name'),
            dict(field='full_name', lbl='!![en]Full Name'),
            dict(field='@organization_id.login', lbl='!![en]Organization'),
            dict(field='repo_group', lbl='!![en]Group')
        ], cols=4, isDefault=True)

    def th_top_custom(self, top):
        top.bar.replaceSlots('vtitle', '')

    def th_top_clone(self, top):
        top.slotToolbar('2,sections@organization_id,*,sections@dynrepogroup,2',
                        childname='organizations', _position='<bar',
                        sections_dynrepogroup_remote=self.sectionsDynRepoGroup)

    def th_top_organization(self, top):
        bar = top.slotToolbar('2,sections@sync_status,10,sections@clone_status,10,sections@repo_status,*,updListBtn,5,updContentBtn,2',
                       childname='repo_filter', _position='<bar')
        bar.updListBtn.slotButton('!![en]Update Repo List',
            action="""PUBLISH table_script_run = {res_type:"action",
                resource:"import_repositories", table:"gnrgh.repository"};""")
        bar.updContentBtn.slotButton('!![en]Update Repo Content',
            action="""PUBLISH table_script_run = {res_type:"action",
                resource:"deep_sync", table:"gnrgh.repository"};""")

    def th_sections_sync_status(self):
        return [
            dict(code='all', caption='!![en]All'),
            dict(code='not_synced', caption='!![en]Not Synced',
                 condition='$last_sync_ts IS NULL'),
            dict(code='synced', caption='!![en]Synced',
                 condition='$sync_status IS TRUE'),
            dict(code='pending', caption='!![en]Pending',
                 condition='$sync_status IS FALSE'),
        ]

    def th_sections_clone_status(self):
        return [
            dict(code='all', caption='!![en]All'),
            dict(code='cloned', caption='!![en]Cloned',
                 condition="$clone_path IS NOT NULL AND $clone_path != ''"),
            dict(code='outdated', caption='!![en]Outdated',
                 condition='$clone_status IS FALSE'),
            dict(code='uptodate', caption='!![en]Up to date',
                 condition='$clone_status IS TRUE'),
            dict(code='not_cloned', caption='!![en]Not Cloned',
                 condition="$clone_path IS NULL OR $clone_path = ''")
        ]

    def th_sections_repo_status(self):
        return [
            dict(code='active', caption='!![en]Active',
                 condition='$archived IS NOT TRUE AND $closure_date IS NULL'),
            dict(code='all', caption='!![en]All'),
            dict(code='archived', caption='!![en]Archived', condition='$archived IS TRUE')
        ]

    @public_method(remote_organization_id='^gnrgh_repository.view.sections.organization_id.current')
    def sectionsDynRepoGroup(self, organization_id=None, **kwargs):
        """Remote sections for repo_group, filtered by selected organization."""
        result = [dict(code='all', caption='!![en]All')]
        if not organization_id:
            return result
        groups = self.db.table('gnrgh.repo_group').query(
            columns='$code,$name',
            where='LOWER($organization_id)=:org_id OR $organization_id IS NULL',
            org_id=organization_id.lower(),
            order_by='$name'
        ).fetch()
        for i,g in enumerate(groups):
            result.append(dict(code=f'r_{i}', caption=g['name'] or g['code'],
                               condition='$repo_group=:repo_group',
                               condition_repo_group=g['code']))
        return result


class ViewFromOrganization(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('name', width='10em')
        r.fieldcell('full_name', width='20em')
        r.fieldcell('description', width='auto')
        r.fieldcell('default_branch', width='8em')
        r.fieldcell('private', width='3em', name='!![en]Priv.', tick=True)
        r.fieldcell('clone_status', width='3em', name='!![en]Clone', semaphore=True)
        r.fieldcell('archived', width='5em', tick=True)
        cs = r.columnset('counters', name='!![en]Counters', background='#5b9bd5')
        cs.fieldcell('branch_count', width='5em', name='!![en]Branches')
        cs.fieldcell('open_issues_count', width='5em', name='!![en]Issues')
        cs.fieldcell('open_pull_requests_count', width='5em', name='!![en]PRs')
        cs = r.columnset('config', name='!![en]Config', background='darkorange')
        cs.fieldcell('repo_group', width='10em')
        cs.fieldcell('commit_policy', width='6em')
        cs.fieldcell('webhook_sync', width='3em', name='!![en]Sync', semaphore=True)
        r.fieldcell('last_commit_ts', width='12em', name='!![en]Last Commit')
        r.fieldcell('pushed_at', width='10em', name='!![en]Last Push')
        r.fieldcell('last_sync_ts', width='12em', name='!![en]Last Sync')

    def th_top_custom(self,top):
        bar = top.bar.replaceSlots('vtitle','sections@sync_status,10,sections@archived,10,sections@dynrepogroup',
                                   sections_dynrepogroup_remote=self.sectionsDynRepoGroup)
        bar.replaceSlots('searchOn','batchAssign,export,searchOn')

    def th_sections_sync_status(self):
        return [
            dict(code='all', caption='!![en]All'),
            dict(code='to_sync', caption='!![en]To Sync',
                 condition='$last_sync_ts IS NULL'),
            dict(code='to_update', caption='!![en]To Update',
                 condition='$last_sync_ts IS NOT NULL AND $has_pending_events IS TRUE'),
            dict(code='synced', caption='!![en]Synced',
                 condition='$last_sync_ts IS NOT NULL AND ($has_pending_events IS NOT TRUE)')
        ]

    def th_sections_archived(self):
        return [
            dict(code='active',caption='!![en]Active',condition='$archived IS NOT TRUE AND $closure_date IS NULL'),
            dict(code='closed',caption='!![en]Closed',condition='$closure_date IS NOT NULL'),
            dict(code='archived',caption='!![en]Archived',condition='$archived IS TRUE')
        ]

    @public_method(remote_organization_id='^#FORM.record.id')
    def sectionsDynRepoGroup(self, organization_id=None, **kwargs):
        """Remote sections for repo_group, filtered by parent organization."""
        result = [dict(code='all', caption='!![en]All')]
        if not organization_id:
            return result
        groups = self.db.table('gnrgh.repo_group').query(
            columns='$code,$name',
            where='$organization_id=:org_id OR $organization_id IS NULL',
            org_id=organization_id,
            order_by='$name'
        ).fetch()
        for i,g in enumerate(groups):
            result.append(dict(code=f'r_{i}', caption=g['name'] or g['code'],
                               condition='$repo_group=:rp',
                               condition_rp=g['code']))
        return result

class Form(BaseComponent):
    css_requires = 'github'

    def th_form(self, form):
        bc = form.center.borderContainer()
        self.repository_config(bc.borderContainer(region='top', datapath='.record', height='155px'))
        tc = bc.tabContainer(region='center', margin='2px')
        self.repository_tabs(tc)

    def th_top_custom(self, top):
        bar = top.bar.replaceSlots('right_placeholder', 'syncbtn,right_placeholder')
        btn = bar.syncbtn.slotButton('!![en]Update from GitHub')
        btn.dataRpc(self.rpc_repo_update,
                    repository_id='=#FORM.record.id',
                    _lockScreen=True,
                    _onResult='this.form.reload();')

    @customizable
    def repository_tabs(self, tc):
        self.localCloneTab(tc.contentPane(title='!![en]Local Clone'))
        self.branchesTab(tc.contentPane(title='!![en]Branches'))
        self.commitsTab(tc.contentPane(title='!![en]Commits'))
        self.issuesTab(tc.contentPane(title='!![en]Issues'))
        self.pullRequestsTab(tc.contentPane(title='!![en]Pull Requests'))
        self.topicsTab(tc.contentPane(title='!![en]Topics'))
        self.labelsTab(tc.contentPane(title='!![en]Labels'))
        self.artifactsTab(tc.contentPane(title='!![en]Artifacts'))
        self.collaboratorsTab(tc.contentPane(title='!![en]Collaborators'))

    def repository_config(self, bc):
        self.repositoryHeader(bc.contentPane(region='center'))
        self.repositoryDetails(bc.borderContainer(region='right', width='400px'))

    def branchesTab(self, pane):
        th = pane.dialogTableHandler(relation='@branches',
                                     viewResource='ViewFromRepository',
                                     addrow=False, delrow=False,
                                     margin='2px', border='1px solid silver', rounded=4)
        th.view.top.bar.replaceSlots('#', '#,syncBtn')
        btn = th.view.top.bar.syncBtn.slotButton('!![en]Update from GitHub')
        btn.dataRpc(self.rpc_repo_syncBranches,
                    repository_id='=#FORM.record.id',
                    _lockScreen=True,
                    _onResult='this.form.reload();')

    def commitsTab(self, pane):
        pane.dialogTableHandler(relation='@commits',
                                viewResource='ViewFromRepository',
                                addrow=False, delrow=False,
                                margin='2px', border='1px solid silver', rounded=4)

    def issuesTab(self, pane):
        th = pane.dialogTableHandler(relation='@issues',
                                     viewResource='ViewFromRepository',
                                     addrow=False, delrow=False,
                                     margin='2px', border='1px solid silver', rounded=4)
        th.view.top.bar.replaceSlots('#', '#,syncBtn')
        btn = th.view.top.bar.syncBtn.slotButton('!![en]Update from GitHub')
        btn.dataRpc(self.rpc_repo_syncIssuesAndPullRequests,
                    repository_id='=#FORM.record.id',
                    _lockScreen=True,
                    _onResult='this.form.reload();')

    def pullRequestsTab(self, pane):
        th = pane.dialogTableHandler(relation='@pull_requests',
                                     viewResource='ViewFromRepository',
                                     addrow=False, delrow=False,
                                     margin='2px', border='1px solid silver', rounded=4)
        th.view.top.bar.replaceSlots('#', '#,syncBtn')
        btn = th.view.top.bar.syncBtn.slotButton('!![en]Update from GitHub')
        btn.dataRpc(self.rpc_repo_syncIssuesAndPullRequests,
                    repository_id='=#FORM.record.id',
                    _lockScreen=True,
                    _onResult='this.form.reload();')

    def collaboratorsTab(self, pane):
        th = pane.dialogTableHandler(relation='@user_connections',
                                     viewResource='ViewCollaborators',
                                     formResource="FormFromRepo",
                                     margin='2px', border='1px solid silver', rounded=4)
        th.view.top.bar.replaceSlots('#', '#,pushBtn,syncBtn')
        btn = th.view.top.bar.syncBtn.slotButton('!![en]Pull from GitHub')
        btn.dataRpc(self.rpc_repo_syncCollaborators,
                    repository_id='=#FORM.record.id',
                    _lockScreen=True,
                    _onResult='this.form.reload();')

    def topicsTab(self, pane):
        th = pane.plainTableHandler(relation='@topic_links',
                                     viewResource='ViewFromRepository',
                                     picker='topic_name',
                                     addrow=False, delrow=True,
                                     margin='2px', border='1px solid silver', rounded=4)
        th.view.top.bar.replaceSlots('#', '#,pushBtn,syncBtn')
        btn = th.view.top.bar.syncBtn.slotButton('!![en]Pull from GitHub')
        btn.dataRpc(self.rpc_repo_syncTopics,
                    repository_id='=#FORM.record.id',
                    _lockScreen=True,
                    _onResult='this.form.reload();')
        pushBtn = th.view.top.bar.pushBtn.slotButton('!![en]Push to GitHub')
        pushBtn.dataRpc(self.rpc_repo_pushTopics,
                    repository_id='=#FORM.record.id',
                    _lockScreen=True,
                    _onResult='this.form.reload();')

    def labelsTab(self, pane):
        th = pane.plainTableHandler(relation='@labels',
                                     viewResource='ViewFromRepository',
                                     addrow=False, delrow=False,
                                     margin='2px', border='1px solid silver', rounded=4)
        th.view.top.bar.replaceSlots('#', '#,syncBtn')
        btn = th.view.top.bar.syncBtn.slotButton('!![en]Pull from GitHub')
        btn.dataRpc(self.rpc_repo_syncLabels,
                    repository_id='=#FORM.record.id',
                    _lockScreen=True,
                    _onResult='this.form.reload();')

    def artifactsTab(self, pane):
        th = pane.dialogTableHandler(relation='@artifacts',
                                     viewResource='ViewFromRepository',
                                     addrow=False, delrow=False,
                                     margin='2px', border='1px solid silver', rounded=4)
        th.view.top.bar.replaceSlots('#', '#,syncBtn')
        btn = th.view.top.bar.syncBtn.slotButton('!![en]Update from GitHub')
        btn.dataRpc(self.rpc_repo_syncArtifacts,
                    repository_id='=#FORM.record.id',
                    _lockScreen=True,
                    _onResult='this.form.reload();')

    def localCloneTab(self, pane):
        bc = pane.borderContainer()
        top = bc.contentPane(region='top', height='120px', datapath='.record')
        fb = top.formlet(cols=4, fld_readOnly=True, margin='3px',
                         border='1px solid silver', rounded=4)
        fb.field('clone_path', colspan=4)
        fb.field('local_branch')
        fb.field('local_head_sha', width='20em')
        fb.field('last_pull_ts')
        fb.field('clone_status', semaphore=True, lbl='!![en]Status')

        bar = bc.contentPane(region='top', height='35px').slotToolbar(
            '2,cloneBtn,5,pullBtn,5,switchBtn,5,diffBtn,*,commitMsg,5,commitBtn,2')
        bar.cloneBtn.slotButton('!![en]Clone / Fetch',
                                action="this.form.publish('cloneRepo')")
        bar.pullBtn.slotButton('!![en]Pull',
                               action="this.form.publish('pullRepo')")
        bar.switchBtn.slotButton('!![en]Switch Branch',
                                 action="this.form.publish('switchBranch')")
        bar.diffBtn.slotButton('!![en]View Diff',
                               action="this.form.publish('viewDiff')")
        bar.commitMsg.textbox(value='^.commit_message', width='20em',
                              placeholder='!![en]Commit message...')
        bar.commitBtn.slotButton('!![en]Commit & Push',
                                 action="this.form.publish('commitAndPush')")

        center = bc.contentPane(region='center', margin='2px')
        center.dataRpc('gnrgh_repository_clone.result', self.rpc_repo_clone,
                       repository_id='=#FORM.record.id',
                       _fired='^.cloneRepo',
                       _lockScreen=True,
                       _onResult='this.form.reload();')
        center.dataRpc('gnrgh_repository_pull.result', self.rpc_repo_pull,
                       repository_id='=#FORM.record.id',
                       _fired='^.pullRepo',
                       _lockScreen=True,
                       _onResult='this.form.reload();')
        center.dataRpc('gnrgh_repository_diff.result', self.rpc_repo_diff,
                       repository_id='=#FORM.record.id',
                       _fired='^.viewDiff',
                       _lockScreen=True)
        center.dataRpc('gnrgh_repository_commit.result', self.rpc_repo_commitAndPush,
                       repository_id='=#FORM.record.id',
                       message='=.commit_message',
                       _fired='^.commitAndPush',
                       _lockScreen=True,
                       _onResult='this.form.reload();')
        center.div('^gnrgh_repository_diff.result',
                   white_space='pre', font_family='monospace',
                   font_size='.85em', overflow='auto',
                   padding='5px', border='1px solid silver',
                   rounded=4, margin='2px', height='100%')

    def repositoryDetails(self, bc):
        fl = bc.contentPane(region='left', width='160px').formlet(
                            cols=1, margin='3px', border='1px solid silver', rounded=4, height='130px')
        fl.img(src='^.avatar_url', height='80px', width='80px')
        fl.div('^.full_name', font_weight='bold')
        fl.a(src='^.html_url', target='_blank', _class='social_icon github_icon')

        fl = bc.contentPane(region='center').formlet(
                            cols=2, margin='3px', border='1px solid silver', rounded=4, height='130px')
        fl.field('private')
        fl.field('archived')
        fl.field('webhook_sync', colspan=2)
        fl.field('closure_date', colspan=2)
        fl.field('closure_reason', tag='simpleTextArea', height='30px', colspan=2)

    def repositoryHeader(self, pane):
        fb = pane.formlet(cols=3, fld_readOnly=True, margin='3px', border='1px solid silver', rounded=4, height='130px')
        fb.field('name')
        fb.field('default_branch')
        fb.field('repo_group')
        fb.field('description', colspan=3)
        fb.field('internal_notes', colspan=3, tag='simpleTextArea', height='30px')

    @public_method
    def rpc_repo_update(self, repository_id=None):
        """Update repository and all dependencies from GitHub."""
        repo_tbl = self.db.table('gnrgh.repository')
        github_id, name, organization, full_name = repo_tbl.readColumns(
            pkey=repository_id,
            columns='$github_id,$name,@organization_id.login,$full_name'
        )
        github_service = self.db.package('gnrgh').getGithubClient()
        owner, repo_name = full_name.split('/')

        # Update repository
        repo_data = github_service.getRepository(github_id=github_id, name=name, organization=organization)
        if repo_data:
            repo_tbl.importRepository(repo_data, pkey=repository_id)

        # Sync branches
        branch_tbl = self.db.table('gnrgh.branch')
        branches = github_service.getBranches(owner=owner, repo=repo_name)
        branch_tbl.importBranches(branches, repository_id=repository_id)

        # Sync issues
        issue_tbl = self.db.table('gnrgh.issue')
        issues = github_service.getIssues(owner=owner, repo=repo_name, state='all')
        for issue_data in issues:
            issue_tbl.importIssue(issue_data, repository_id=repository_id)

        # Sync pull requests
        pr_tbl = self.db.table('gnrgh.pull_request')
        pull_requests = github_service.getPullRequests(owner=owner, repo=repo_name, state='all')
        for pr_data in pull_requests:
            pr_tbl.importPullRequest(pr_data, repository_id=repository_id)

        # Sync topics
        topic_link_tbl = self.db.table('gnrgh.gh_topic_link')
        topics = github_service.getRepositoryTopics(owner=owner, repo=repo_name)
        topic_link_tbl.syncTopics(topics, repository_id=repository_id)

        # Sync labels
        label_tbl = self.db.table('gnrgh.gh_repo_label')
        labels = github_service.getRepositoryLabels(owner=owner, repo=repo_name)
        label_tbl.syncLabels(labels, repository_id=repository_id)

        # Sync collaborators from sw-role topics
        connection_tbl = self.db.table('gnrgh.gh_user_connection')
        connection_tbl.syncMembersFromTopics(repository_id=repository_id)

        # Update last sync timestamp
        from datetime import datetime
        with repo_tbl.recordToUpdate(pkey=repository_id) as rec:
            rec['last_sync_ts'] = datetime.utcnow()

        self.db.commit()

    @public_method
    def rpc_repo_syncBranches(self, repository_id=None):
        """Sync branches from GitHub for this repository."""
        repo_tbl = self.db.table('gnrgh.repository')
        branch_tbl = self.db.table('gnrgh.branch')

        full_name = repo_tbl.readColumns(pkey=repository_id, columns='$full_name')
        if not full_name:
            return

        owner, repo_name = full_name.split('/')

        github_service = self.db.package('gnrgh').getGithubClient()
        branches = github_service.getBranches(owner=owner, repo=repo_name)

        branch_tbl.importBranches(branches, repository_id=repository_id)

    @public_method
    def rpc_repo_syncIssuesAndPullRequests(self, repository_id=None):
        """Sync issues and pull requests from GitHub for this repository."""
        repo_tbl = self.db.table('gnrgh.repository')
        issue_tbl = self.db.table('gnrgh.issue')
        pr_tbl = self.db.table('gnrgh.pull_request')

        # Get repository info
        full_name = repo_tbl.readColumns(pkey=repository_id, columns='$full_name')
        if not full_name:
            return

        owner, repo_name = full_name.split('/')

        github_service = self.db.package('gnrgh').getGithubClient()

        # Sync issues (state='all' to get open and closed)
        issues = github_service.getIssues(owner=owner, repo=repo_name, state='all')
        for issue_data in issues:
            # importIssue skips PRs automatically (checks for pull_request field)
            issue_tbl.importIssue(issue_data, repository_id=repository_id)

        # Sync pull requests
        pull_requests = github_service.getPullRequests(owner=owner, repo=repo_name, state='all')
        for pr_data in pull_requests:
            pr_tbl.importPullRequest(pr_data, repository_id=repository_id)

        self.db.commit()

    @public_method
    def rpc_repo_syncCollaborators(self, repository_id=None):
        """Sync collaborators from GitHub for this repository."""
        repo_tbl = self.db.table('gnrgh.repository')
        user_tbl = self.db.table('gnrgh.gh_user')
        connection_tbl = self.db.table('gnrgh.gh_user_connection')

        full_name = repo_tbl.readColumns(pkey=repository_id, columns='$full_name')
        if not full_name:
            return

        owner, repo_name = full_name.split('/')

        github_service = self.db.package('gnrgh').getGithubClient()

        # Fetch collaborators from GitHub
        collaborators = github_service.getRepoCollaborators(owner=owner, repo=repo_name)

        # Get role assignments from local topics (already resolved via sysRecord)
        role_assignments = connection_tbl.getRoleTopics(repository_id=repository_id)
        role_by_username = {username: role for role, username in role_assignments}

        # Delete existing repository collaborator connections
        connection_tbl.deleteSelection(
            where='$repository_id=:repository_id',
            repository_id=repository_id
        )

        # Import collaborators and create connections
        for collab_data in collaborators:
            user_pkey = user_tbl.importUser(collab_data)
            if user_pkey:
                username = collab_data.get('login')
                # Use role from topic if available, otherwise None
                repo_role_code = role_by_username.get(username)
                connection_tbl.addConnection(
                    gh_user_id=user_pkey,
                    repo_role_code=repo_role_code,
                    repository_id=repository_id
                )

        self.db.commit()

    @public_method
    def rpc_repo_syncArtifacts(self, repository_id=None):
        """Sync artifacts from GitHub for this repository."""
        repo_tbl = self.db.table('gnrgh.repository')
        artifact_tbl = self.db.table('gnrgh.gh_artifact')

        full_name, organization_id = repo_tbl.readColumns(
            pkey=repository_id,
            columns='$full_name,$organization_id'
        )
        if not full_name:
            return

        owner, repo_name = full_name.split('/')

        github_service = self.db.package('gnrgh').getGithubClient()
        packages = github_service.getPackages(organization=owner)

        # Filter artifacts belonging to this repository and import them
        for pkg_data in packages:
            repo_data = pkg_data.get('repository')
            if repo_data and repo_data.get('full_name') == full_name:
                artifact_tbl.importArtifact(pkg_data, organization_id=organization_id)

        self.db.commit()

    @public_method
    def rpc_repo_syncTopics(self, repository_id=None):
        """Sync topics from GitHub for this repository."""
        repo_tbl = self.db.table('gnrgh.repository')
        topic_link_tbl = self.db.table('gnrgh.gh_topic_link')

        full_name = repo_tbl.readColumns(pkey=repository_id, columns='$full_name')
        if not full_name:
            return

        owner, repo_name = full_name.split('/')

        github_service = self.db.package('gnrgh').getGithubClient()
        topics = github_service.getRepositoryTopics(owner=owner, repo=repo_name)

        topic_link_tbl.syncTopics(topics, repository_id=repository_id)

        self.db.commit()

    @public_method
    def rpc_repo_syncLabels(self, repository_id=None):
        """Sync labels from GitHub for this repository."""
        repo_tbl = self.db.table('gnrgh.repository')
        label_tbl = self.db.table('gnrgh.gh_repo_label')

        full_name = repo_tbl.readColumns(pkey=repository_id, columns='$full_name')
        if not full_name:
            return

        owner, repo_name = full_name.split('/')

        github_service = self.db.package('gnrgh').getGithubClient()
        labels = github_service.getRepositoryLabels(owner=owner, repo=repo_name)

        label_tbl.syncLabels(labels, repository_id=repository_id)

        self.db.commit()

    @public_method
    def rpc_repo_pushTopics(self, repository_id=None):
        """Push local topics to GitHub for this repository."""
        repo_tbl = self.db.table('gnrgh.repository')
        topic_link_tbl = self.db.table('gnrgh.gh_topic_link')

        full_name = repo_tbl.readColumns(pkey=repository_id, columns='$full_name')
        if not full_name:
            return

        owner, repo_name = full_name.split('/')

        # Get current topics from local DB
        local_topics = topic_link_tbl.query(
            columns='$topic_name',
            where='$repository_id=:repository_id',
            repository_id=repository_id
        ).fetch()

        topics = [row['topic_name'] for row in local_topics]

        # Push to GitHub
        github_service = self.db.package('gnrgh').getGithubClient()
        github_service.setRepositoryTopics(owner=owner, repo=repo_name, topics=topics)

    @public_method
    def rpc_repo_pushCollaborators(self, repository_id=None):
        """Push local collaborators to GitHub for this repository."""
        repo_tbl = self.db.table('gnrgh.repository')
        connection_tbl = self.db.table('gnrgh.gh_user_connection')

        full_name = repo_tbl.readColumns(pkey=repository_id, columns='$full_name')
        if not full_name:
            return

        owner, repo_name = full_name.split('/')

        # Get collaborators from local DB with their roles
        local_collaborators = connection_tbl.query(
            columns='@gh_user_id.login,@repo_role_code.repo_level',
            where='$repository_id=:repository_id',
            repository_id=repository_id
        ).fetch()

        github_service = self.db.package('gnrgh').getGithubClient()

        for collab in local_collaborators:
            login = collab['@gh_user_id.login']
            repo_level = collab['@repo_role_code.repo_level']
            if login and repo_level:
                github_service.addCollaborator(
                    owner=owner,
                    repo=repo_name,
                    username=login,
                    permission=repo_level
                )

    @public_method
    def rpc_repo_clone(self, repository_id=None):
        """Clone or fetch a repository locally."""
        repo_tbl = self.db.table('gnrgh.repository')
        repo_tbl.cloneRepository(repository_id)
        self.db.commit()

    @public_method
    def rpc_repo_pull(self, repository_id=None):
        """Pull latest changes for a cloned repository."""
        repo_tbl = self.db.table('gnrgh.repository')
        repo_tbl.pullRepository(repository_id)
        self.db.commit()

    @public_method
    def rpc_repo_switchBranch(self, repository_id=None, branch=None):
        """Switch the local clone to a different branch."""
        repo_tbl = self.db.table('gnrgh.repository')
        repo_tbl.switchBranch(repository_id, branch)
        self.db.commit()

    @public_method
    def rpc_repo_diff(self, repository_id=None):
        """Get diff of local uncommitted changes."""
        repo_tbl = self.db.table('gnrgh.repository')
        return repo_tbl.getRepoDiff(repository_id)

    @public_method
    def rpc_repo_commitAndPush(self, repository_id=None, message=None):
        """Commit local changes and push to remote."""
        repo_tbl = self.db.table('gnrgh.repository')
        repo_tbl.commitAndPush(repository_id, message)
        self.db.commit()

    def th_options(self):
        return dict(dialog_parentRatio=.8)

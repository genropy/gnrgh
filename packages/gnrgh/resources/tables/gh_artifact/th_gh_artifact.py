#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method


class View(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('name', width='15em')
        r.fieldcell('package_type', width='8em')
        r.fieldcell('visibility', width='6em')
        r.fieldcell('@organization_id.login', name='Organization', width='10em')
        r.fieldcell('@repository_id.name', name='Repository', width='12em')
        r.fieldcell('version_count', width='6em')
        r.fieldcell('num_versions', name='Synced', width='5em')
        r.fieldcell('github_updated_at', width='10em')

    def th_order(self):
        return 'name'

    def th_query(self):
        return dict(column='name', op='contains', val='')

    def th_top_bar(self, top):
        top.slotToolbar('5,sections@package_type,10,sections@organization_id,*',
                        childname='filters', _position='<bar')


class ViewFromOrganization(BaseComponent):
    """View for artifacts within an organization context"""

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('name', width='15em')
        r.fieldcell('package_type', width='8em')
        r.fieldcell('visibility', width='6em')
        r.fieldcell('@repository_id.name', name='Repository', width='12em')
        r.fieldcell('version_count', width='6em')
        r.fieldcell('num_versions', name='Synced', width='5em')
        r.fieldcell('github_created_at', width='10em')
        r.fieldcell('github_updated_at', width='10em')

    def th_order(self):
        return 'name'


class ViewFromRepository(BaseComponent):
    """View for artifacts within a repository context"""

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('name', width='15em')
        r.fieldcell('package_type', width='8em')
        r.fieldcell('visibility', width='6em')
        r.fieldcell('version_count', width='6em')
        r.fieldcell('github_updated_at', width='10em')

    def th_order(self):
        return 'name'


class Form(BaseComponent):

    def th_form(self, form):
        bc = form.center.borderContainer()
        self.artifactHeader(bc.contentPane(region='top', datapath='.record', padding='10px'))
        tc = bc.tabContainer(region='center')
        self.versionsTab(tc.contentPane(title='!![en]Versions'))
        self.metadataTab(tc.contentPane(title='!![en]Metadata'))

    def artifactHeader(self, pane):
        fb = pane.formlet(cols=4, fld_readOnly=True)
        fb.field('name')
        fb.field('package_type')
        fb.field('visibility')
        fb.field('version_count')
        fb.field('@organization_id.login', lbl='Organization')
        fb.field('@repository_id.full_name', lbl='Repository')
        fb.field('github_created_at')
        fb.field('github_updated_at')
        fb.field('html_url', colspan=4)

        box = fb.div(_class='button_box', colspan=4)
        box.button('!![en]Update from GitHub',
                   iconClass='iconbox refresh',
                   disabled='^#FORM.controller.is_newrecord'
                   ).dataRpc(self.rpc_updateArtifactFromGithub,
                             artifact_id='=#FORM.record.id',
                             _lockScreen=True,
                             _onResult='this.form.reload();')

    def versionsTab(self, pane):
        th = pane.dialogTableHandler(relation='@versions',
                                     viewResource='ViewFromArtifact',
                                     addrow=False, delrow=False)
        th.view.top.bar.replaceSlots('searchOn', 'syncBtn,searchOn')
        th.view.top.bar.syncBtn.slotButton('!![en]Sync',
                                           iconClass='iconbox icnRefresh',
                                           action='FIRE .sync;')
        th.dataRpc('dummy', self.rpc_syncVersions,
                   artifact_id='=#FORM.record.id',
                   _fired='^.sync',
                   _lockScreen=True,
                   _onResult='this.form.reload();')

    def metadataTab(self, pane):
        pane.tree(storepath='#FORM.record.metadata',
                       margin='5px')

    @public_method
    def rpc_updateArtifactFromGithub(self, artifact_id=None):
        """Refresh single artifact from GitHub."""
        artifact_tbl = self.db.table('gnrgh.gh_artifact')
        name, package_type, org_login = artifact_tbl.readColumns(
            pkey=artifact_id,
            columns='$name,$package_type,@organization_id.login'
        )

        github_service = self.db.package('gnrgh').getGithubClient()
        packages = github_service.getPackages(
            organization=org_login,
            package_type=package_type
        )

        # Find matching artifact
        for pkg_data in packages:
            if pkg_data['name'] == name:
                artifact_tbl.importArtifact(pkg_data, pkey=artifact_id)
                break

        self.db.commit()

    @public_method
    def rpc_syncVersions(self, artifact_id=None):
        """Sync versions for this artifact from GitHub."""
        artifact_tbl = self.db.table('gnrgh.gh_artifact')
        version_tbl = self.db.table('gnrgh.gh_artifact_version')

        name, package_type, org_login = artifact_tbl.readColumns(
            pkey=artifact_id,
            columns='$name,$package_type,@organization_id.login'
        )

        github_service = self.db.package('gnrgh').getGithubClient()
        versions = github_service.getPackageVersions(
            organization=org_login,
            package_type=package_type,
            package_name=name
        )

        for version_data in versions:
            version_tbl.importArtifactVersion(version_data, artifact_id=artifact_id)

        self.db.commit()

    def th_options(self):
        return dict(dialog_height='500px', dialog_width='800px')

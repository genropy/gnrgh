#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent


class View(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('organization_name', width='10em')
        r.fieldcell('repo_name', width='12em')
        r.fieldcell('name', width='15em')
        r.fieldcell('commit_sha', width='20em')
        r.fieldcell('commit_count', width='6em')
        r.fieldcell('protected', width='6em')
        r.fieldcell('is_default', width='6em')
        r.fieldcell('last_commit_ts', width='12em')

    def th_order(self):
        return 'organization_name,repo_name,name'

    def th_query(self):
        return dict(column='name', op='contains', val='')

    def th_sections_sync_status(self):
        return [
            dict(code='all', caption='!![en]All'),
            dict(code='synced', caption='!![en]Synced',
                 condition='$last_sync_ts IS NOT NULL'),
            dict(code='to_sync', caption='!![en]To Sync',
                 condition='$last_sync_ts IS NULL')
        ]

    def th_top_bar(self, top):
        top.slotToolbar('2,sections@sync_status,*',
                       childname='sync_filter', _position='<bar')

    def th_groupedStruct(self, struct):
        r = struct.view().rows()
        r.fieldcell('organization_name', width='10em', name='!![en]Organization')
        r.fieldcell('repo_name', width='12em', name='!![en]Repository')
        r.cell('_grp_count', name='!![en]Branches', width='6em',
               group_aggr='sum', dtype='L', childname='_grp_count')


class ViewFromRepository(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('name', width='15em')
        r.fieldcell('commit_sha', width='25em')
        r.fieldcell('protected', width='6em')
        r.fieldcell('is_default', width='6em')
        r.fieldcell('last_commit_ts', width='12em')

    def th_order(self):
        return 'name'


class Form(BaseComponent):

    def th_form(self, form):
        bc = form.center.borderContainer()
        self.branchHeader(bc.contentPane(region='top', datapath='.record'))
        self.branchCommits(bc.contentPane(region='center'))

    def branchHeader(self, pane):
        fb = pane.formlet(cols=3)
        fb.field('name', readOnly=True)
        fb.field('@repository_id.full_name', readOnly=True)
        fb.field('commit_sha', readOnly=True)
        fb.field('protected', readOnly=True)
        fb.field('is_default', readOnly=True)
        fb.field('last_commit_ts', readOnly=True)

    def branchCommits(self, pane):
        pane.plainTableHandler(relation='@branch_commits',
                               viewResource='ViewFromBranch',
                               addrow=False, delrow=False,
                               margin='2px', border='1px solid silver', rounded=4)

    def th_options(self):
        return dict(dialog_parentRatio=.8)


class FormFromRepository(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.div(margin='10px').formbuilder(cols=2, border_spacing='4px',
                                                  fld_width='100%', width='100%')
        fb.field('name', readOnly=True)
        fb.field('commit_sha', readOnly=True, colspan=2)
        fb.field('protected', readOnly=True)
        fb.field('is_default', readOnly=True)
        fb.field('last_commit_ts', readOnly=True)

    def th_options(self):
        return dict(dialog_height='300px', dialog_width='500px')

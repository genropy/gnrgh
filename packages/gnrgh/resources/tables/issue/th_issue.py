#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method

class View(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('number', width='5em')
        r.fieldcell('title', width='25em')
        r.fieldcell('@repository_id.full_name', name='!![en]Repository', width='15em')
        r.fieldcell('state', width='6em')
        r.fieldcell('@author_id.login', name='!![en]Author', width='10em')
        r.fieldcell('github_created_at', name='!![en]Created At', width='10em')

    def th_order(self):
        return 'github_created_at:d'

    def th_query(self):
        return dict(column='title', op='contains', val='')

    def th_queryBySample(self):
        return dict(fields=[
            dict(field='number', lbl='!![en]Number', width='5em'),
            dict(field='title', lbl='!![en]Title'),
            dict(field='@repository_id.full_name', lbl='!![en]Repository'),
            dict(field='@author_id.login', lbl='!![en]Author')
        ], cols=4, isDefault=True)

    def th_groupedStruct(self, struct):
        "Organization / Repository"
        r = struct.view().rows()
        r.fieldcell('@repository_id.@organization_id.login', name='Organization', width='15em')
        r.fieldcell('@repository_id.full_name', name='Repository', width='20em')
        r.cell('_grp_count', name='All', width='5em', group_aggr='sum', dtype='L')
        r.cell('cnt_user', name='Mine', width='5em', group_aggr='sum', dtype='L')


    def th_sections_organization(self):
        org_rows = self.db.table('gnrgh.organization').query(
            columns='$id, $login',
            order_by='$login'
        ).fetch()
        sections = [dict(code='all', caption='!![en]All')]
        for org in org_rows:
            sections.append(dict(
                code=org['id'],
                caption=org['login'],
                condition='$organization_name=:org_name',
                condition_org_name=org['login']
            ))
        return sections

    def th_sections_repogroup(self):
        groups = self.db.table('gnrgh.repo_group').query(
            columns='$code,$name',
            order_by='$name'
        ).fetch()
        sections = [dict(code='all', caption='!![en]All')]
        for g in groups:
            sections.append(dict(
                code=g['code'],
                caption=g['name'] or g['code'],
                condition='$repo_group=:rg',
                condition_rg=g['code']
            ))
        return sections

    def th_top_partition_bar(self, top):
        top.slotToolbar('5,sections@organization,5,sections@repogroup,*',
                       childname='partition_bar', _position='<bar')

    def th_top_status_bar(self, top):
        top.slotToolbar('5,sections@state,*,sections@userConnection',
                       childname='status_bar', _position='<bar')

    def th_sections_userConnection(self):
        return [
            dict(code='all', caption='!![en]All'),
            dict(code='my', caption='!![en]My Issues', condition='$is_user_author IS TRUE'),
            dict(code='connected', caption='!![en]Connected', condition='$is_user_connected IS TRUE')
        ]



class ViewFromRepository(BaseComponent):
    """View for issues within a repository context (used in repository tabs)"""

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('number', width='5em')
        r.fieldcell('title', width='25em')
        r.fieldcell('state', width='6em')
        r.fieldcell('@author_id.login', name='!![en]Author', width='10em')
        r.fieldcell('github_created_at', name='!![en]Created At', width='10em')

    def th_order(self):
        return 'github_created_at:d'

    def th_query(self):
        return dict(column='title', op='contains', val='')

    
    def th_top_custom(self,top):
        top.bar.replaceSlots('vtitle','sections@state',section_state_all_end=True)


class Form(BaseComponent):
    css_requires = "github"
    
    def th_form(self, form):
        bc = form.center.borderContainer()
        top = bc.borderContainer(region='top', datapath='.record', padding='5px', height='130px')
        self.issueHeader(top.contentPane(region='center'))
        self.issueReference(top.contentPane(region='right', width='150px'))
        
        tabs = bc.tabContainer(region='center')
        self.issueBody(tabs.contentPane(title='!![en]Body', datapath=".record"))
        self.issueComments(tabs.contentPane(title='!![en]Comments'))

    def issueHeader(self, pane):
        fl = pane.formlet(cols=3, border_spacing='4px', border='1px solid silver', rounded=4, height='110px')
        fl.field('title', colspan=2, readOnly=True)
        fl.field('state', readOnly=True, width='6em')
        fl.field('@repository_id.full_name', readOnly=True, lbl='!![en]Repository', colspan=2)
        fl.field('@author_id.login', readOnly=True)
        fl.field('html_url', colspan=4, readOnly=True)
    
    def issueReference(self, pane):
        fl = pane.formlet(cols=1, border_spacing='4px', border='1px solid silver', rounded=4, height='110px')
        fl.field('number', readOnly=True, width='5em')
        fl.field('github_created_at', readOnly=True)
        fl.a(src='^.html_url', target='_blank', _class='social_icon github_icon')

    def issueBody(self, pane):
        pane.MdEditor(value='^.body', height='100%', viewer=True)
        
    def issueComments(self, pane):
        pane.dialogTableHandler(relation='@comments',
                                viewResource='ViewFromIssue',
                                formResource='FormFromIssue',
                                addrow=False,
                                delrow=False)

    def th_options(self):
        return dict(dialog_height='500px', dialog_width='700px')

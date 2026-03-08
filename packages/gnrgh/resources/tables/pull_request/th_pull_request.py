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

        st = r.columnset('status', name='!![en]Status')
        st.fieldcell('state', width='6em')
        st.fieldcell('draft', width='5em')
        st.fieldcell('merged', width='5em')

        br = r.columnset('branch', name='!![en]Branch', background='darkgreen')
        br.fieldcell('head_ref', name='!![en]From', width='10em')
        br.fieldcell('base_ref', name='!![en]To', width='10em')

        pp = r.columnset('people', name='!![en]People', background='darkorange')
        pp.fieldcell('@author_id.login', name='!![en]Author', width='10em')
        pp.fieldcell('github_created_at', width='10em')

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
        top.slotToolbar('2,sections@organization,5,sections@repogroup,2',
                       childname='partition_bar', _position='<bar')

    def th_top_status_bar(self, top):
        top.slotToolbar('2,sections@state,*,sections@userConnection',
                       childname='status_bar', _position='<bar')

    def th_sections_userConnection(self):
        return [
            dict(code='all', caption='!![en]All'),
            dict(code='my', caption='!![en]My PRs', condition='$is_user_author IS TRUE'),
            dict(code='connected', caption='!![en]Connected', condition='$is_user_connected IS TRUE')
        ]



class ViewFromRepository(BaseComponent):
    """View for pull requests within a repository context (used in repository tabs)"""

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('number', width='5em')
        r.fieldcell('title', width='25em')

        st = r.columnset('status', name='!![en]Status')
        st.fieldcell('state', width='6em')
        st.fieldcell('draft', width='5em')
        st.fieldcell('merged', width='5em')

        br = r.columnset('branch', name='!![en]Branch', background='darkgreen')
        br.fieldcell('head_ref', name='!![en]From', width='10em')
        br.fieldcell('base_ref', name='!![en]To', width='10em')

        pp = r.columnset('people', name='!![en]People', background='darkorange')
        pp.fieldcell('@author_id.login', name='!![en]Author', width='10em')
        pp.fieldcell('github_created_at', name='!![en]Created At', width='10em')

    def th_order(self):
        return 'github_created_at:d'

    def th_query(self):
        return dict(column='title', op='contains', val='')
    
    def th_top_custom(self,top):
        top.bar.replaceSlots('vtitle','sections@state',section_state_all_end=True)



class Form(BaseComponent):

    def th_form(self, form):
        bc = form.center.borderContainer()
        self.prHeader(bc.contentPane(region='top', datapath='.record', padding='10px'))
        self.prBody(bc.contentPane(region='center', padding='10px'))

    def prHeader(self, pane):
        fb = pane.formbuilder(cols=4, border_spacing='4px', fld_width='100%')
        fb.field('number', readOnly=True, width='5em')
        fb.field('title', colspan=2, readOnly=True)
        fb.field('state', readOnly=True, width='6em')
        fb.field('@repository_id.full_name', readOnly=True, colspan=2)
        fb.field('@author_id.login', readOnly=True)
        fb.field('github_created_at', readOnly=True)
        fb.field('head_ref', readOnly=True, lbl='!![en]From Branch')
        fb.field('base_ref', readOnly=True, lbl='!![en]To Branch')
        fb.field('draft', readOnly=True)
        fb.field('merged', readOnly=True)
        fb.field('html_url', colspan=4, readOnly=True)

    def prBody(self, pane):
        pane.simpleTextArea(value='^.record.body', height='100%',
                            readOnly=True, lbl='!![en]Body')

    def th_options(self):
        return dict(dialog_height='500px', dialog_width='700px')

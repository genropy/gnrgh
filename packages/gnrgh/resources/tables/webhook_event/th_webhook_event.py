#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('received_at')
        r.fieldcell('delivery_id')
        r.fieldcell('event')
        r.fieldcell('action')
        r.fieldcell('repo_id')
        r.fieldcell('organization_id')

    def th_order(self):
        return 'received_at:d'

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
                condition='$organization_id=:org_id',
                condition_org_id=org['id']
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

    def th_query(self):
        return dict(column='delivery_id', op='contains', val='')

class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('delivery_id')
        fb.field('event')
        fb.field('action')
        fb.field('repo_id')
        fb.field('organization_id')
        fb.field('received_at')
        fb.field('payload')


    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')

class ViewFromOrganization(BaseComponent):
    """View for events within an organization context"""

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('received_at', width='12em')
        r.fieldcell('delivery_id', width='15em')
        r.fieldcell('event', width='10em')
        r.fieldcell('action', width='8em')
        r.fieldcell('repo_id', width='12em')
        r.fieldcell('issue', width='8em')
        r.fieldcell('pull_request', width='8em')

    def th_order(self):
        return 'received_at:d'

class ViewFromRepository(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('received_at', width='12em')
        r.fieldcell('event', width='10em')
        r.fieldcell('action', width='8em')
        r.fieldcell('issue', width='8em')
        r.fieldcell('pull_request', width='8em')
        r.fieldcell('delivery_id', width='15em')

    def th_order(self):
        return 'received_at:d'

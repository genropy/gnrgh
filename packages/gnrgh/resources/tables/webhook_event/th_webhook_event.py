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
        return 'received_at'

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

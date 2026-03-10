#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent


class View(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('name', width='15em')
        r.fieldcell('color', width='8em')
        r.fieldcell('description', width='30em')
        r.fieldcell('@repository_id.full_name', name='Repository', width='20em')

    def th_order(self):
        return 'name'

    def th_query(self):
        return dict(column='name', op='contains', val='')

    def th_top_bar(self, top):
        top.slotToolbar('5,sections@repository_id,*',
                        childname='filters', _position='<bar')


class ViewFromRepository(BaseComponent):
    """View for labels within a repository context"""

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('name', width='15em')
        r.fieldcell('color', width='8em')
        r.fieldcell('description', width='30em')

    def th_order(self):
        return 'name'


class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px', fld_width='100%')
        fb.field('name', readOnly=True)
        fb.field('color', readOnly=True)
        fb.field('description', colspan=2, readOnly=True)
        fb.field('@repository_id.full_name', lbl='Repository', readOnly=True)

    def th_options(self):
        return dict(dialog_height='250px', dialog_width='500px')

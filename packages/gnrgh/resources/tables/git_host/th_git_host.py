#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent


class View(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('description', width='15em')
        r.fieldcell('type', width='8em')
        r.fieldcell('url', width='25em')

    def th_order(self):
        return 'description'

    def th_query(self):
        return dict(column='description', op='contains', val='')


class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=1, border_spacing='4px', fld_width='100%')
        fb.field('description')
        fb.field('type')
        fb.field('url')
        fb.field('token', type='password')
        fb.field('webhook_secret', type='password')

    def th_options(self):
        return dict(dialog_height='300px', dialog_width='500px')

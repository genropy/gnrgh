#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method

class View(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('login', width='12em')
        r.fieldcell('user_type', width='8em')
        r.fieldcell('html_url', width='20em')

    def th_order(self):
        return 'login'

    def th_query(self):
        return dict(column='login', op='contains', val='')


class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px', fld_width='100%')
        fb.field('login', readOnly=True)
        fb.field('user_type', readOnly=True)
        fb.field('html_url', colspan=2, readOnly=True)
        fb.img(src='^.avatar_url', height='80px', width='80px',
               colspan=2, style='border-radius: 50%;')

    def th_options(self):
        return dict(dialog_height='300px', dialog_width='400px')

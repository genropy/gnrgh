#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent


class View(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('repo_full_name', width='15em')
        r.fieldcell('name', width='15em')
        r.fieldcell('commit_sha', width='20em')
        r.fieldcell('protected', width='6em')
        r.fieldcell('is_default', width='6em')

    def th_order(self):
        return '@repository_id.full_name,name'

    def th_query(self):
        return dict(column='name', op='contains', val='')


class ViewFromRepository(BaseComponent):
    """View for branches within a repository context"""

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('name', width='15em')
        r.fieldcell('commit_sha', width='25em')
        r.fieldcell('protected', width='6em')
        r.fieldcell('is_default', width='6em')

    def th_order(self):
        return 'name'


class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.div(margin='10px').formbuilder(cols=2, border_spacing='4px',
                                                  fld_width='100%', width='100%')
        fb.field('name', readOnly=True)
        fb.field('@repository_id.full_name', readOnly=True)
        fb.field('commit_sha', readOnly=True, colspan=2)
        fb.field('protected', readOnly=True)
        fb.field('is_default', readOnly=True)

    def th_options(self):
        return dict(dialog_height='300px', dialog_width='500px')


class FormFromRepository(BaseComponent):
    """Form for branches within a repository context"""

    def th_form(self, form):
        pane = form.record
        fb = pane.div(margin='10px').formbuilder(cols=2, border_spacing='4px',
                                                  fld_width='100%', width='100%')
        fb.field('name', readOnly=True)
        fb.field('commit_sha', readOnly=True, colspan=2)
        fb.field('protected', readOnly=True)
        fb.field('is_default', readOnly=True)

    def th_options(self):
        return dict(dialog_height='300px', dialog_width='500px')

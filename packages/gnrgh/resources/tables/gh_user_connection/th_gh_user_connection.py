#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent


class View(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('@gh_user_id.login', name='User', width='12em')
        r.fieldcell('connection_type', width='10em')
        r.fieldcell('@gh_user_id.user_type', name='Type', width='8em')

    def th_order(self):
        return '@gh_user_id.login'

    def th_query(self):
        return dict(column='@gh_user_id.login', op='contains', val='')


class ViewMembers(BaseComponent):
    """View for organization members"""

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('@gh_user_id.login', name='User', width='12em')
        r.fieldcell('membership', width='8em')
        r.fieldcell('repo_role_code', name='Role', width='8em')
        r.fieldcell('connection_type', width='10em')
        r.fieldcell('@gh_user_id.user_type', name='Type', width='8em')
        r.fieldcell('@gh_user_id.html_url', name='Profile', width='20em')
        r.fieldcell('@gh_user_id.adm_user_id', name='ADM User', width='10em')

    def th_order(self):
        return '@gh_user_id.login'


class ViewCollaborators(BaseComponent):
    """View for repository collaborators"""

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('@gh_user_id.login', name='User', width='12em')
        r.fieldcell('repo_role_code', width='10em')
        r.fieldcell('@gh_user_id.html_url', name='Profile', width='20em')

    def th_order(self):
        return '@gh_user_id.login'
    
class FormFromRepo(BaseComponent):
    def th_form(self, form):
        pane = form.record
        fb = pane.formlet(cols=1)
        fb.field('@gh_user_id.login', readOnly=True)
        fb.field('repo_role_code')

    def th_options(self):
        return dict(dialog_height='200px', dialog_width='250px',modal=True)

class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px', fld_width='100%')
        fb.field('@gh_user_id.login', readOnly=True)
        fb.field('connection_type', readOnly=True)

    def th_options(self):
        return dict(dialog_height='200px', dialog_width='400px')

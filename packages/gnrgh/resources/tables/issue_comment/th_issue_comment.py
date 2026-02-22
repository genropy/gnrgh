#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method

class View(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('@author_id.login', name='!![en]Author', width='10em')
        r.fieldcell('body_preview', width='30em')
        r.fieldcell('github_created_at', name='!![en]Created', width='10em')
        r.fieldcell('@issue_id.number', name='!![en]Issue #', width='6em')

    def th_order(self):
        return 'github_created_at:a'

    def th_query(self):
        return dict(column='body', op='contains', val='')


class ViewFromIssue(BaseComponent):
    """View for comments within an issue context"""

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('@author_id.login', name='!![en]Author', width='10em')
        r.fieldcell('body_preview', width='35em')
        r.fieldcell('github_created_at', name='!![en]Created', width='12em')

    def th_order(self):
        return 'github_created_at:a'


class Form(BaseComponent):
    css_requires = "github"

    def th_form(self, form):
        bc = form.center.borderContainer()
        top = bc.contentPane(region='top', datapath='.record', padding='5px', height='60px')
        self.commentHeader(top)
        self.commentBody(bc.contentPane(region='center', datapath='.record'))

    def commentHeader(self, pane):
        fl = pane.formlet(cols=3, border_spacing='4px', border='1px solid silver', rounded=4)
        fl.field('@author_id.login', readOnly=True, lbl='!![en]Author')
        fl.field('github_created_at', readOnly=True, lbl='!![en]Created')
        fl.a(src='^.html_url', target='_blank', _class='social_icon github_icon')

    def commentBody(self, pane):
        pane.MdEditor(value='^.body', height='100%', viewer=True)

    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')


class FormFromIssue(BaseComponent):
    """Form for comments within an issue context"""
    css_requires = "github"

    def th_form(self, form):
        bc = form.center.borderContainer()
        top = bc.contentPane(region='top', datapath='.record', padding='5px', height='50px')
        self.commentHeader(top)
        self.commentBody(bc.contentPane(region='center', datapath='.record'))

    def commentHeader(self, pane):
        fl = pane.formlet(cols=2, border_spacing='4px', border='1px solid silver', rounded=4)
        fl.field('@author_id.login', readOnly=True, lbl='!![en]Author')
        fl.field('github_created_at', readOnly=True, lbl='!![en]Created')

    def commentBody(self, pane):
        pane.MdEditor(value='^.body', height='100%', viewer=True)

    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')

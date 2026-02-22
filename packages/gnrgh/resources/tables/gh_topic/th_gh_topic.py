#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent


class View(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('name', width='20em')

    def th_order(self):
        return 'name'

    def th_query(self):
        return dict(column='name', op='contains', val='')


class Form(BaseComponent):

    def th_form(self, form):
        bc = form.center.borderContainer()
        self.topicHeader(bc.contentPane(region='top', datapath='.record', padding='10px'))
        self.linksTab(bc.contentPane(region='center'))

    def topicHeader(self, pane):
        fb = pane.formlet(cols=1)
        fb.field('name', readOnly='^#FORM.controller.is_newrecord?=!#v')

    def linksTab(self, pane):
        pane.dialogTableHandler(relation='@links',
                                viewResource='ViewFromTopic')

    def th_options(self):
        return dict(dialog_height='400px', dialog_width='500px')

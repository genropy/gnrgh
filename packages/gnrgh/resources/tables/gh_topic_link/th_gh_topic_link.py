#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent


class View(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('topic_name', width='15em')
        r.fieldcell('@repository_id.full_name', name='Repository', width='20em')

    def th_order(self):
        return 'topic_name'

    def th_query(self):
        return dict(column='topic_name', op='contains', val='')

    def th_top_bar(self, top):
        top.slotToolbar('2,sections@repository_id,*',
                        childname='filters', _position='<bar')


class ViewFromRepository(BaseComponent):
    """View for topic links within a repository context"""

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('topic_name', width='20em')

    def th_order(self):
        return 'topic_name'


class ViewFromTopic(BaseComponent):
    """View for topic links within a topic context"""

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('@repository_id.full_name', name='Repository', width='20em')

    def th_order(self):
        return '@repository_id.full_name'


class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px', fld_width='100%')
        fb.field('topic_name', readOnly=True)
        fb.field('@repository_id.full_name', lbl='Repository', readOnly=True)

    def th_options(self):
        return dict(dialog_height='200px', dialog_width='400px')

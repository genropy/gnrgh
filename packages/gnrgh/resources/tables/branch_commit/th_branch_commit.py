#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent


class ViewFromBranch(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('@commit_id.sha', width='12em', name='!![en]SHA')
        r.fieldcell('@commit_id.author_name', width='10em', name='!![en]Author')
        r.fieldcell('@commit_id.author_date', width='12em', name='!![en]Date')
        r.fieldcell('@commit_id.message', width='30em', name='!![en]Message')
        r.fieldcell('@commit_id.files_changed', width='6em', name='!![en]Files Changed')

    def th_order(self):
        return '@commit_id.author_date:d'


class ViewFromCommit(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('@branch_id.name', width='15em', name='!![en]Branch')
        r.fieldcell('@branch_id.is_default', width='5em', name='!![en]Default')

    def th_order(self):
        return '@branch_id.name'

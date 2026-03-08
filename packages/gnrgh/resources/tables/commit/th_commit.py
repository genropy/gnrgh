#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent


class View(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('repo_full_name', width='15em')
        r.fieldcell('branch_names', width='12em')
        r.fieldcell('sha', width='12em')
        r.fieldcell('author_name', width='10em')
        r.fieldcell('author_date', width='12em')
        r.fieldcell('message', width='30em')
        r.fieldcell('files_changed', width='6em')

    def th_order(self):
        return 'author_date:d'

    def th_query(self):
        return dict(column='message_text', op='fulltext', val='')

    def th_queryBySample(self):
        return dict(fields=[
            dict(field='sha', lbl='!![en]SHA', width='12em'),
            dict(field='author_name', lbl='!![en]Author'),
            dict(field='message', lbl='!![en]Message'),
            dict(field='@repository_id.full_name', lbl='!![en]Repository')
        ], cols=4, isDefault=True)

    def th_sections_organization(self):
        org_rows = self.db.table('gnrgh.organization').query(
            columns='$id, $login',
            order_by='$login'
        ).fetch()
        sections = [dict(code='all', caption='!![en]All')]
        for org in org_rows:
            sections.append(dict(
                code=org['id'],
                caption=org['login'],
                condition='$organization_name=:org_name',
                condition_org_name=org['login']
            ))
        return sections

    def th_sections_repogroup(self):
        groups = self.db.table('gnrgh.repo_group').query(
            columns='$code,$name',
            order_by='$name'
        ).fetch()
        sections = [dict(code='all', caption='!![en]All')]
        for g in groups:
            sections.append(dict(
                code=g['code'],
                caption=g['name'] or g['code'],
                condition='$repo_group=:rg',
                condition_rg=g['code']
            ))
        return sections

    def th_top_partition_bar(self, top):
        top.slotToolbar('2,sections@organization,5,sections@repogroup,2',
                       childname='partition_bar', _position='<bar')


class ViewFromRepository(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('sha', width='12em')
        r.fieldcell('branch_names', width='15em')
        r.fieldcell('author_name', width='10em')
        r.fieldcell('author_date', width='12em')
        r.fieldcell('message', width='30em')
        r.fieldcell('files_changed', width='6em')

    def th_order(self):
        return 'author_date:d'


class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.div(margin='10px').formbuilder(cols=2, border_spacing='4px',
                                                  fld_width='100%', width='100%')
        fb.field('sha', readOnly=True, colspan=2)
        fb.field('@repository_id.full_name', readOnly=True, lbl='!![en]Repository')
        fb.field('author_name', readOnly=True)
        fb.field('author_email', readOnly=True)
        fb.field('author_date', readOnly=True)
        fb.field('files_changed', readOnly=True)
        fb.field('message', readOnly=True, colspan=2, tag='simpleTextArea', height='150px')

    def th_options(self):
        return dict(dialog_height='450px', dialog_width='600px')

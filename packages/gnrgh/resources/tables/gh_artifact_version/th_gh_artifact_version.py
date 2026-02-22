#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method


class View(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('name', width='15em')
        r.fieldcell('@artifact_id.name', name='Artifact', width='12em')
        r.fieldcell('@artifact_id.package_type', name='Type', width='8em')
        r.fieldcell('license', width='8em')
        r.fieldcell('github_created_at', width='10em')

    def th_order(self):
        return 'github_created_at:d'

    def th_query(self):
        return dict(column='name', op='contains', val='')


class ViewFromArtifact(BaseComponent):
    """View for versions within an artifact context"""

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('name', width='15em')
        r.fieldcell('description', width='20em')
        r.fieldcell('license', width='8em')
        r.fieldcell('github_created_at', width='12em')
        r.fieldcell('github_updated_at', width='12em')

    def th_order(self):
        return 'github_created_at:d'


class Form(BaseComponent):

    def th_form(self, form):
        bc = form.center.borderContainer()
        self.versionHeader(bc.contentPane(region='top', datapath='.record', padding='10px'))
        self.versionMetadata(bc.contentPane(region='center', padding='10px'))

    def versionHeader(self, pane):
        fb = pane.formlet(cols=3, fld_readOnly=True)
        fb.field('name')
        fb.field('@artifact_id.name', lbl='Artifact')
        fb.field('@artifact_id.package_type', lbl='Type')
        fb.field('description', colspan=3)
        fb.field('license')
        fb.field('github_created_at')
        fb.field('github_updated_at')
        fb.field('html_url', colspan=3)

    def versionMetadata(self, pane):
        pane.tree(storepath='#FORM.record.metadata',
                       margin='5px')
    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')

# -*- coding: utf-8 -*-

import os

class GnrCustomWebPage(object):
    py_requires = 'gnrcomponents/gnride_dark/gnride_dark:GnrIdeDark'

    def main(self, root, **kwargs):
        clone_base_path = self.db.application.getPreference('clone_base_path', pkg='gnrgh')
        if not clone_base_path:
            clone_base_path = os.path.join(os.path.expanduser('~'), '.gnrgh', 'clones')
        root.attributes.update(overflow='hidden')
        root.gnrIdeFrame(datapath='main', sourceFolders=clone_base_path)

# encoding: utf-8


class AppPref(object):
    def prefpane_gnrgh(self, parent, **kwargs):
        fb = parent.contentPane(margin='2px', **kwargs).formbuilder()
        fb.div('!![en]Access token and webhook secret are set on each Git Host',
               margin_bottom='8px')
        fb.textbox(value='^.commit_policy', lbl='!![en]Commit Policy (default)',
                   placeholder='5', tip='!![en]e.g. 5 = last 5 commits, 3m = last 3 months')
        fb.textbox(value='^.clone_base_path', lbl='!![en]Clone Base Path',
                   placeholder='~/.gnrgh/clones',
                   tip='!![en]Local path for repository clones',
                   width='60em')

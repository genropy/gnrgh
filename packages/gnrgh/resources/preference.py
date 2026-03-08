# encoding: utf-8


class AppPref(object):
    def prefpane_gnrgh(self, parent, **kwargs):
        fb = parent.contentPane(margin='2px', **kwargs).formbuilder()
        fb.textbox(value='^.access_token', lbl='!![en]Access Token',
                   placeholder='!![en]Leave empty to use system gh token')
        fb.textbox(value='^.webhook_secret', lbl='!![en]Webhook Secret')
        fb.textbox(value='^.commit_policy', lbl='!![en]Commit Policy (default)',
                   placeholder='5', tip='!![en]e.g. 5 = last 5 commits, 3m = last 3 months')
        fb.textbox(value='^.clone_base_path', lbl='!![en]Clone Base Path',
                   placeholder='~/.gnrgh/clones',
                   tip='!![en]Local path for repository clones',
                   width='60em')

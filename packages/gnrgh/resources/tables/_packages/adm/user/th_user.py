#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.core.gnrdecorator import oncalled
from gnr.web.gnrbaseclasses import BaseComponent


class Form(BaseComponent):

    @oncalled
    def adm_user_maintc(self, tc, **kwargs):
        """Show the git accounts linked to the user, one per git_host.

        The link is set on the account (gnrgh.gh_user.adm_user_id): deleting a
        row here would delete the account, so the grid is read-only.
        """
        tc.contentPane(title='!![en]Git accounts').plainTableHandler(
            relation='@gh_accounts', viewResource='ViewFromAdmUser',
            addrow=False, delrow=False, margin='2px')

# -*- coding: utf-8 -*-

# frameindex.py
# Created by Francesco Porcari on 2011-04-06.
# Copyright (c) 2011 Softwell. All rights reserved.
# Frameindex component

from gnr.web.gnrwebpage import BaseComponent
        
class LoginComponent(BaseComponent):
    def onAuthenticating_github(self,avatar,rootenv=None):
        if avatar.user_id:
            rootenv['gh_user_id'] = self.db.table('adm.user').readColumns(pkey=avatar.user_id,columns='$gh_user_id')

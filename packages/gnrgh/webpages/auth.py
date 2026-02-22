# -*- coding: UTF-8 -*-
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrlang import GnrException
from gnr.core.gnrbag import Bag
import json

class GnrCustomWebPage(object):
    py_requires = 'gnrcomponents/externalcall:BaseRpc'

    @public_method
    def getToken(self, code=None, state=None, **kwargs):
        if not code:
            raise GnrException('!![en]Something got wrong, no code received')
        try:
            state = json.loads(state)
            auth_mode = state['auth_mode']
            if auth_mode == 'MAIN':
                self.mainAuthentication(code=code, state=state)
            elif auth_mode == 'USER':
                self.userAuthentication(code=code, state=state)
            elif auth_mode == 'CUST':
                self.customAuthentication(code=code, state=state)
            else:
                raise GnrException('!![en]Something got wrong, no authentication mode specified')
            return f"Authentication successful"
        except:
            raise GnrException('!![en]Something got wrong, authentication failed')
        
    def mainAuthentication(self, code=None, state=None):
        service = self.site.getService(service_name=state['service_name'], service_type='repository')
        with self.db.table('sys.service').recordToUpdate(
                                            where='$service_name=:sn AND $service_type=:st',
                                            sn=state['service_name'], st='repository', bagFields=True) as service_rec:
            access_token, refresh_token = service.getToken(code=code)
            service_rec['parameters'].update(Bag(access_token=access_token, refresh_token=refresh_token))
        self.db.commit()
        self.db.table('sys.service').notifyDbUpdate(service_rec['service_identifier'])
    
    def userAuthentication(self, code=None, state=None):
        service = self.site.getService(service_name=state['service_name'], service_type='repository')
        with self.db.table('adm.user').recordToUpdate(state['user_id'], bagFields=True) as user_rec:
            access_token, refresh_token = service.getToken(code=code)
            parameters_bag = Bag()
            parameters_bag.setItem(state['implementation'], Bag(access_token=access_token, refresh_token=refresh_token))
            user_rec['preferences'].update(Bag(github=parameters_bag))
        self.db.commit()
        self.db.table('adm.user').notifyDbUpdate(state['user_id'])
        
    def customAuthentication(self, code=None, state=None):
        "This method is used to set access_token and refresh_token in a custom record in a custom table"
        service = self.site.getService(service_name=state['service_name'], service_type='repository')
        custom_table = state['custom_table']
        custom_pkey = state['custom_pkey']
        with self.db.table(state['custom_table']).recordToUpdate(custom_pkey, bagFields=True) as custom_rec:
            custom_rec[f"{state['implementation']}_access_token"], custom_rec[f"{state['implementation']}_refresh_token"] = service.getToken(code=code)
        self.db.commit()
        self.db.table(custom_table).notifyDbUpdate(custom_pkey)
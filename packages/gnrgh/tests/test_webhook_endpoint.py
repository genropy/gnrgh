# encoding: utf-8
"""receiveWebhook: the git_host comes from the url, never from the payload."""
import hashlib
import hmac
import json
import os

import pytest

from gnr.core.gnrlang import gnrImport, GnrException

EP = os.path.join(os.path.dirname(__file__), '..', 'webpages', 'ep.py')


class FakeRequest(object):
    def __init__(self, body, headers):
        self.body = body
        self.headers = headers

    def get_header(self, name):
        return self.headers.get(name)

    def get_data(self, cache=True):
        return self.body


def make_page(db, payload, secret, forgejo=False):
    body = json.dumps(payload).encode('utf-8')
    headers = {'X-GitHub-Delivery': 'd-ep-%s' % forgejo, 'X-GitHub-Event': 'ping',
               'X-Hub-Signature-256': 'sha256=' + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()}
    if forgejo:
        headers['X-Forgejo-Event'] = 'ping'
    page_cls = gnrImport(EP).GnrCustomWebPage
    page = page_cls.__new__(page_cls)  # receiveWebhook reads only self.db and self.request
    page.db = db
    page.request = FakeRequest(body, headers)
    return page


def test_forgejo_webhook_without_git_host_id_is_rejected(db, hosts):
    page = make_page(db, dict(zen='x'), 's3cret', forgejo=True)
    with pytest.raises(GnrException):
        page.receiveWebhook()


def test_github_webhook_without_git_host_id_uses_the_github_secret(db, hosts):
    git_host_tbl = db.table('gnrgh.git_host')
    with git_host_tbl.recordToUpdate(hosts['github']) as rec:
        rec['webhook_secret'] = 'gh-secret'
    db.commit()
    result = make_page(db, dict(zen='x'), 'gh-secret').receiveWebhook()
    assert result['success'] is True
    with pytest.raises(GnrException):
        make_page(db, dict(zen='y'), 'wrong').receiveWebhook()

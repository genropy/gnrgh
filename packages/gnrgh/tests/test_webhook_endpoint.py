# encoding: utf-8
"""receiveWebhook: the git_host comes from the url; without it, a GitHub event
goes to github.com and a Forgejo event to the host of its repository url."""
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


def test_forgejo_webhook_without_git_host_id_uses_the_repository_url(db, hosts):
    git_host_tbl = db.table('gnrgh.git_host')
    with git_host_tbl.recordToUpdate(hosts['forgejo']) as rec:
        rec['webhook_secret'] = 'fj-secret'
    db.commit()
    web_url = git_host_tbl.webUrl(hosts['forgejo'])
    payload = dict(zen='x', repository=dict(html_url=web_url + '/acme/widget'))
    result = make_page(db, payload, 'fj-secret', forgejo=True).receiveWebhook()
    assert result['success'] is True
    # the github secret does not sign an event for the forgejo host
    with pytest.raises(GnrException):
        make_page(db, payload, 'gh-secret', forgejo=True).receiveWebhook()
    # no repository url, or a server nobody knows: rejected
    with pytest.raises(GnrException):
        make_page(db, dict(zen='x'), 'fj-secret', forgejo=True).receiveWebhook()
    with pytest.raises(GnrException):
        make_page(db, dict(zen='x', repository=dict(html_url='https://other.example/a/b')),
                  'fj-secret', forgejo=True).receiveWebhook()


def test_github_webhook_without_git_host_id_uses_the_github_secret(db, hosts):
    git_host_tbl = db.table('gnrgh.git_host')
    with git_host_tbl.recordToUpdate(hosts['github']) as rec:
        rec['webhook_secret'] = 'gh-secret'
    db.commit()
    result = make_page(db, dict(zen='x'), 'gh-secret').receiveWebhook()
    assert result['success'] is True
    with pytest.raises(GnrException):
        make_page(db, dict(zen='y'), 'wrong').receiveWebhook()

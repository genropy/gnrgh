# encoding: utf-8
"""A gnrgh application on a temporary PostgreSQL server.

The server is started by testing.postgresql and stopped at the end of the
session: nothing touches the developer's databases. The schema is built from
the model; the mandatory sysRecords (gnrgh.git_host GITHUB) are created by
dbUpgradeBroadcast, as `gnr db migrate -u` does.
"""
import os

import pytest
from testing.postgresql import Postgresql

from gnr.app.gnrapp import GnrApp

INSTANCE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'instances', 'gnrgh')


@pytest.fixture(scope='session')
def db():
    previous_lang = os.environ.get('LANG')
    os.environ['LANG'] = 'en_GB.UTF-8'  # initdb needs a proper locale
    try:
        pg_instance = Postgresql()
    finally:
        if previous_lang is None:
            os.environ.pop('LANG', None)
        else:
            os.environ['LANG'] = previous_lang
    pg_conf = pg_instance.dsn()
    pg_conf.pop('database', None)
    app = None
    try:
        app = GnrApp(os.path.abspath(INSTANCE_PATH),
                     db_attrs=dict(implementation='postgres', dbname='gnrgh_pytest', **pg_conf))
        app.db.model.check(applyChanges=True)
        app.dbUpgradeBroadcast()
        app.db.commit()
        yield app.db
    finally:
        if app is not None:
            app.db.closeConnection()
        pg_instance.stop()


@pytest.fixture
def hosts(db):
    """The github.com host and a Forgejo host, each with an organization."""
    git_host_tbl = db.table('gnrgh.git_host')
    github = git_host_tbl.githubHost()
    forgejo = git_host_tbl.query(where="$type='forgejo'", columns='$id').fetch()
    if forgejo:
        forgejo = forgejo[0]['id']
    else:
        record = git_host_tbl.newrecord(description='hub', url='https://hub.example/api/v1',
                                        type='forgejo', token='t')
        git_host_tbl.insert(record)
        forgejo = record['id']
    org_tbl = db.table('gnrgh.organization')
    organizations = {}
    for name, host in (('github', github), ('forgejo', forgejo)):
        organizations[name] = org_tbl.importOrganization(
            dict(id=7, login='acme', name='Acme', type='Organization'), git_host_id=host)
    db.commit()
    return dict(github=github, forgejo=forgejo, organizations=organizations)


REPO_PAYLOAD = dict(id=100, name='widget', full_name='acme/widget', description='',
                    default_branch='main', private=False, archived=False,
                    owner=dict(id=7, login='acme', type='Organization'))


def issue_payload(number, user_id=42):
    return dict(id=42, number=number, title=f'Issue {number}', body='', state='open',
                user=dict(id=user_id, login=f'user{user_id}', type='User'))

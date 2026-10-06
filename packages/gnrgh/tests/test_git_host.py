# encoding: utf-8
"""Issue #2: rows are identified by (git_host, server id), not by server id alone."""
import os

from gnr.core.gnrlang import gnrImport

from conftest import REPO_PAYLOAD, issue_payload

UPGRADE_SCRIPT = os.path.join(os.path.dirname(__file__), '..', 'lib', 'upgrades', '0001_git_host.py')


def import_repo(db, hosts, host):
    return db.table('gnrgh.repository').importRepository(
        dict(REPO_PAYLOAD), organization_id=hosts['organizations'][host])


def test_same_ids_on_two_servers_are_two_rows(db, hosts):
    issue_tbl = db.table('gnrgh.issue')
    issue_ids = {}
    for host in ('github', 'forgejo'):
        repository_id = import_repo(db, hosts, host)
        issue_ids[host] = issue_tbl.importIssue(issue_payload(1), repository_id=repository_id)
    db.commit()

    assert issue_ids['github'] != issue_ids['forgejo']
    authors = {host: issue_tbl.readColumns(pkey=pkey, columns='$author_id,$git_host_id')
               for host, pkey in issue_ids.items()}
    assert authors['github'][0] != authors['forgejo'][0]
    assert authors['github'][1] == hosts['github']
    assert authors['forgejo'][1] == hosts['forgejo']
    users = db.table('gnrgh.gh_user').query(where='$github_id=42', columns='$git_host_id').fetch()
    assert sorted(u['git_host_id'] for u in users) == sorted([hosts['github'], hosts['forgejo']])


def test_one_adm_user_many_accounts(db, hosts):
    user_tbl = db.table('gnrgh.gh_user')
    adm_user_tbl = db.table('adm.user')
    accounts = {host: user_tbl.importUser(dict(id=42, login='someone'), git_host_id=hosts[host])
                for host in ('github', 'forgejo')}
    adm_user = adm_user_tbl.insert(adm_user_tbl.newrecord(username='someone', status='conf'))
    for pkey in accounts.values():
        with user_tbl.recordToUpdate(pkey) as rec:
            rec['adm_user_id'] = adm_user['id']
    db.commit()

    linked = user_tbl.query(where='$adm_user_id=:u', u=adm_user['id'],
                            columns='$git_host_id').fetch()
    assert sorted(a['git_host_id'] for a in linked) == sorted([hosts['github'], hosts['forgejo']])


def test_webhook_events_link_to_their_server(db, hosts):
    event_tbl = db.table('gnrgh.webhook_event')
    issue_tbl = db.table('gnrgh.issue')
    for host in ('github', 'forgejo'):
        import_repo(db, hosts, host)
    event_ids = {}
    for n, host in enumerate(('github', 'forgejo')):
        payload = dict(action='opened', issue=issue_payload(5), repository=dict(REPO_PAYLOAD),
                       organization=dict(id=7, login='acme'))
        event_ids[host] = event_tbl.storeEvent(payload, git_host_id=hosts[host], event='issues',
                                               delivery_id=f'd-{n}')
    db.commit()

    for host, event_id in event_ids.items():
        issue_id, event_host = event_tbl.readColumns(pkey=event_id, columns='$issue_id,$git_host_id')
        assert event_host == hosts[host]
        assert issue_tbl.readColumns(pkey=issue_id, columns='$git_host_id') == hosts[host]


def test_upgrade_script_is_idempotent_and_reports_collisions(db, hosts, capsys):
    user_tbl = db.table('gnrgh.gh_user')
    issue_tbl = db.table('gnrgh.issue')
    # an account imported before git_host existed, referenced from two servers
    collided = user_tbl.insert(user_tbl.newrecord(github_id=999, login='collided'))['id']
    for host in ('github', 'forgejo'):
        repository_id = import_repo(db, hosts, host)
        issue_id = issue_tbl.importIssue(issue_payload(9), repository_id=repository_id)
        issue_tbl.batchUpdate(dict(author_id=collided), pkey=issue_id)
    # an unreferenced account, and an issue without host
    lonely = user_tbl.insert(user_tbl.newrecord(github_id=998, login='lonely'))['id']
    issue_tbl.batchUpdate(dict(git_host_id=None), where='$number=9 AND $git_host_id=:h',
                          h=hosts['forgejo'])
    db.commit()

    upgrade = gnrImport(UPGRADE_SCRIPT)
    upgrade.main(db)
    db.commit()
    first = capsys.readouterr().out
    assert f'gh_user {collided}' in first
    assert user_tbl.readColumns(pkey=collided, columns='$git_host_id') is None
    assert user_tbl.readColumns(pkey=lonely, columns='$git_host_id') == hosts['github']
    assert issue_tbl.query(where='$git_host_id IS NULL').count() == 0

    snapshot = sorted((r['id'], r['git_host_id']) for r in user_tbl.query(columns='$id,$git_host_id').fetch())
    upgrade.main(db)
    db.commit()
    second = capsys.readouterr().out
    assert f'gh_user {collided}' in second
    assert sorted((r['id'], r['git_host_id']) for r in user_tbl.query(columns='$id,$git_host_id').fetch()) == snapshot


def test_repository_action_uses_the_client_of_its_host(db, hosts, monkeypatch):
    """rpc_repo_syncCollaborators on a Forgejo repository talks to the Forgejo host."""
    from gnrpkg.gnrgh.github_client import GithubClient
    th_repository = gnrImport(os.path.join(
        os.path.dirname(__file__), '..', 'resources', 'tables', 'repository', 'th_repository.py'))
    repository_id = import_repo(db, hosts, 'forgejo')
    urls_called = []

    def fake_collaborators(self, owner=None, repo=None, **kwargs):
        urls_called.append(self.api_url)
        return [dict(id=77, login='collab77', type='User')]
    monkeypatch.setattr(GithubClient, 'getRepoCollaborators', fake_collaborators)

    page = th_repository.Form.__new__(th_repository.Form)  # the method reads only self.db
    page.db = db
    page.rpc_repo_syncCollaborators(repository_id=repository_id)

    forgejo_url = db.table('gnrgh.git_host').readColumns(pkey=hosts['forgejo'], columns='$url')
    assert urls_called == [forgejo_url]
    collab = db.table('gnrgh.gh_user').query(where='$github_id=77', columns='$git_host_id').fetch()
    assert [c['git_host_id'] for c in collab] == [hosts['forgejo']]


def test_host_without_token_never_uses_the_local_gh_token(db, hosts):
    import pytest
    git_host_tbl = db.table('gnrgh.git_host')
    with git_host_tbl.recordToUpdate(hosts['forgejo']) as rec:
        rec['token'] = None
    db.commit()
    try:
        with pytest.raises(ValueError):
            git_host_tbl.getClient(hosts['forgejo'])
    finally:
        with git_host_tbl.recordToUpdate(hosts['forgejo']) as rec:
            rec['token'] = 't'
        db.commit()


def test_upgrade_script_moves_adm_user_link_and_creates_hosts(db, hosts, capsys):
    """Step 5 (adm.user.gh_user_id -> gh_user.adm_user_id) and step 1 (one host per
    api_url, organizations of one host with different tokens reported)."""
    user_tbl = db.table('gnrgh.gh_user')
    adm_user_tbl = db.table('adm.user')
    git_host_tbl = db.table('gnrgh.git_host')
    org_tbl = db.table('gnrgh.organization')
    # the legacy columns, as they stay in a migrated database
    db.execute('ALTER TABLE adm.adm_user ADD COLUMN IF NOT EXISTS gh_user_id character(22)')
    db.execute('ALTER TABLE gnrgh.gnrgh_organization ADD COLUMN IF NOT EXISTS api_url text, '
               'ADD COLUMN IF NOT EXISTS access_token text')
    account = user_tbl.importUser(dict(id=501, login='legacy'), git_host_id=hosts['github'])
    legacy_user = adm_user_tbl.insert(adm_user_tbl.newrecord(username='legacy', status='conf'))['id']
    db.execute('UPDATE adm.adm_user SET gh_user_id=:a WHERE id=:u', sqlargs=dict(a=account, u=legacy_user))
    for login, url, token in (('one', 'https://one.example/api/v1', 'tok1'),
                              ('two_a', 'https://two.example/api/v1', 'tokA'),
                              ('two_b', 'https://two.example/api/v1', 'tokB')):
        org = org_tbl.insert(org_tbl.newrecord(login=login, github_id=1, git_host_id=None))
        db.execute('UPDATE gnrgh.gnrgh_organization SET api_url=:u, access_token=:t WHERE id=:o',
                   sqlargs=dict(u=url, t=token, o=org['id']))
    db.commit()

    gnrImport(UPGRADE_SCRIPT).main(db)
    db.commit()
    out = capsys.readouterr().out

    assert user_tbl.readColumns(pkey=account, columns='$adm_user_id') == legacy_user
    hosts_by_url = {h['url']: h for h in git_host_tbl.query(columns='$url,$token,$type').fetch()}
    assert hosts_by_url['https://one.example/api/v1']['token'] == 'tok1'
    assert hosts_by_url['https://two.example/api/v1']['token'] == 'tokA'
    assert hosts_by_url['https://two.example/api/v1']['type'] == 'forgejo'
    assert 'token differs' in out
    linked = {r['login']: r['url'] for r in org_tbl.query(
        where='$login IN :l', l=['one', 'two_a', 'two_b'],
        columns='$login,@git_host_id.url AS url').fetch()}
    assert linked == {'one': 'https://one.example/api/v1',
                      'two_a': 'https://two.example/api/v1',
                      'two_b': 'https://two.example/api/v1'}

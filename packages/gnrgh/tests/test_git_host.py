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

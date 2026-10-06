# encoding: utf-8
"""Identify imported rows by git server (issue #2).

Fills git_host_id on the nine imported tables, moves organization.api_url /
access_token into gnrgh.git_host and adm.user.gh_user_id into
gnrgh.gh_user.adm_user_id. The old columns leave the model but stay in the
database: they are read with raw SQL.

Idempotent: every step works on rows with git_host_id IS NULL. Rows the
script cannot decide (a gh_user referenced from two servers, organizations of
one server with different tokens) are printed and left to a manual fix.
"""

# webhook_event rows read per query in step 6
EVENTS_BATCH = 500

# path from each imported table to the git_host of its organization
ORGANIZATION_HOST = {
    'repository': '@organization_id.git_host_id',
    'issue': '@repository_id.@organization_id.git_host_id',
    'pull_request': '@repository_id.@organization_id.git_host_id',
    'issue_comment': '@issue_id.@repository_id.@organization_id.git_host_id',
    'gh_repo_label': '@repository_id.@organization_id.git_host_id',
    'gh_artifact': '@organization_id.git_host_id',
    'gh_artifact_version': '@artifact_id.@organization_id.git_host_id',
}

# columns pointing to gh_user, with the git_host of the pointing row
GH_USER_REFERENCES = (
    ('issue', 'author_id', '$git_host_id'),
    ('pull_request', 'author_id', '$git_host_id'),
    ('issue_comment', 'author_id', '$git_host_id'),
    ('gh_artifact', 'owner_id', '$git_host_id'),
    ('organization', 'org_user_id', '$git_host_id'),
    ('gh_user_connection', 'gh_user_id', 'COALESCE(@organization_id.git_host_id,'
                                         '@repository_id.git_host_id,'
                                         '@issue_id.git_host_id,'
                                         '@pull_request_id.git_host_id)'),
)


def column_exists(db, schema, table, column):
    return bool(db.execute(
        """SELECT 1 FROM information_schema.columns
           WHERE table_schema=:s AND table_name=:t AND column_name=:c""",
        sqlargs=dict(s=schema, t=table, c=column)).fetchall())


def main(db):
    git_host_tbl = db.table('gnrgh.git_host')
    org_tbl = db.table('gnrgh.organization')
    user_tbl = db.table('gnrgh.gh_user')
    github_host_id = git_host_tbl.githubHost()

    # 1. hosts: github.com from the package preference, one per distinct api_url
    print('\t git_host: github.com and one per organization.api_url')
    with git_host_tbl.recordToUpdate(github_host_id) as host:
        if not host['token']:
            host['token'] = db.application.getPreference('access_token', pkg='gnrgh')
        if not host['webhook_secret']:
            host['webhook_secret'] = db.application.getPreference('webhook_secret', pkg='gnrgh')
    host_by_url = {}   # api_url -> git_host pkey
    token_by_url = {}  # api_url -> token of that git_host
    organizations = []  # (pkey, api_url, access_token) of the organizations still to assign
    if column_exists(db, 'gnrgh', 'gnrgh_organization', 'api_url'):
        organizations = db.execute(
            """SELECT id, api_url, access_token FROM gnrgh.gnrgh_organization
               WHERE git_host_id IS NULL ORDER BY __ins_ts""").fetchall()
    for org_id, api_url, access_token in organizations:
        if not api_url:
            continue
        if api_url not in host_by_url:
            existing = git_host_tbl.query(where='$url=:u', u=api_url, columns='$id,$token').fetch()
            if existing:
                host_by_url[api_url] = existing[0]['id']
                token_by_url[api_url] = existing[0]['token']
            else:
                record = git_host_tbl.newrecord(description=api_url.split('/')[2],
                                                url=api_url, type='forgejo', token=access_token)
                git_host_tbl.insert(record)
                host_by_url[api_url] = record['id']
                token_by_url[api_url] = access_token
        elif access_token and access_token != token_by_url[api_url]:
            print(f'\t   organization {org_id}: token differs from the git_host of {api_url}, fix by hand')

    # 2. organization.git_host_id from its api_url (empty = github.com)
    print('\t organization.git_host_id')
    for org_id, api_url, access_token in organizations:
        org_tbl.batchUpdate(dict(git_host_id=host_by_url[api_url] if api_url else github_host_id),
                            pkey=org_id)
    org_tbl.batchUpdate(dict(git_host_id=github_host_id), where='$git_host_id IS NULL')

    # 3. imported tables: the host of their organization
    for table, host_path in ORGANIZATION_HOST.items():
        print(f'\t {table}.git_host_id')
        tbl = db.table(f'gnrgh.{table}')
        rows = tbl.query(where='$git_host_id IS NULL', columns=f'$id,{host_path} AS host_id',
                         addPkeyColumn=False).fetch()
        for row in rows:
            if row['host_id']:
                tbl.batchUpdate(dict(git_host_id=row['host_id']), pkey=row['id'])

    # 4. gh_user: the host of the rows that reference it
    print('\t gh_user.git_host_id')
    hosts_by_user = {}  # gh_user pkey -> set of git_host pkeys
    for table, column, host_path in GH_USER_REFERENCES:
        rows = db.table(f'gnrgh.{table}').query(
            where=f'${column} IS NOT NULL AND @{column}.git_host_id IS NULL',
            columns=f'${column} AS user_id,{host_path} AS host_id', addPkeyColumn=False).fetch()
        for row in rows:
            if row['host_id']:
                hosts_by_user.setdefault(row['user_id'], set()).add(row['host_id'])
    collided = []
    for user_id, hosts in hosts_by_user.items():
        if len(hosts) > 1:
            collided.append(user_id)
        else:
            user_tbl.batchUpdate(dict(git_host_id=hosts.pop()), pkey=user_id)
    # accounts nobody references were imported from github.com, the only server
    # that created gh_user rows before git_host existed
    where = '$git_host_id IS NULL'
    if collided:
        where += ' AND $id NOT IN :collided'
    user_tbl.batchUpdate(dict(git_host_id=github_host_id), where=where, collided=collided)
    for user_id in collided:
        login, github_id = user_tbl.readColumns(pkey=user_id, columns='$login,$github_id')
        print(f'\t   gh_user {user_id} ({login}, id {github_id}) is referenced from more than one '
              f'server: git_host_id left empty, fix by hand')

    # 5. gh_user.adm_user_id from the old adm.user.gh_user_id
    if column_exists(db, 'adm', 'adm_user', 'gh_user_id'):
        print('\t gh_user.adm_user_id')
        links = db.execute(
            'SELECT id, gh_user_id FROM adm.adm_user WHERE gh_user_id IS NOT NULL').fetchall()
        for adm_user_id, gh_user_id in links:
            user_tbl.batchUpdate(dict(adm_user_id=adm_user_id),
                                 where='$id=:u AND $adm_user_id IS NULL', u=gh_user_id)

    # 6. webhook_event: host and linked rows from the payload
    print('\t webhook_event.git_host_id, issue_id, pull_request_id')
    event_tbl = db.table('gnrgh.webhook_event')
    issue_tbl = db.table('gnrgh.issue')
    pr_tbl = db.table('gnrgh.pull_request')
    # payloads are read EVENTS_BATCH rows at a time: the table holds the raw
    # payload of every event ever received, too much to parse in one fetch.
    # Every batch sets git_host_id, so the next query returns the rows after it.
    while True:
        events = event_tbl.query(where='$git_host_id IS NULL',
                                 columns='$id,$payload,@organization_id.git_host_id AS org_host_id,'
                                         '@repo_id.git_host_id AS repo_host_id',
                                 addPkeyColumn=False, order_by='$id', limit=EVENTS_BATCH).fetch()
        if not events:
            break
        for event in events:
            host_id = event['org_host_id'] or event['repo_host_id'] or github_host_id
            payload = event['payload']
            updater = dict(git_host_id=host_id)
            if payload:
                updater['issue_id'] = issue_tbl.pkeyFromExternal(host_id, payload['issue.id'])
                updater['pull_request_id'] = pr_tbl.pkeyFromExternal(host_id, payload['pull_request.id'])
            event_tbl.batchUpdate(updater, pkey=event['id'])

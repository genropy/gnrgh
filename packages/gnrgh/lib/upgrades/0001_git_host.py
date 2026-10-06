# encoding: utf-8
"""Identify imported rows by git server (issue #2).

Fills git_host_id on the nine imported tables, moves organization.api_url /
access_token into gnrgh.git_host and adm.user.gh_user_id into
gnrgh.gh_user.adm_user_id. The old columns leave the model but stay in the
database: they are read with raw SQL.

Every step after the first is one SQL statement per table: the production
tables hold tens of thousands of rows (webhook_event alone 66k, 400 MB of
payload) and one ORM update per row took hours.

Idempotent: every step works on rows with git_host_id IS NULL. Rows the
script cannot decide (a gh_user referenced from two servers, organizations of
one server with different tokens) are printed and left to a manual fix.
"""

# imported table -> SQL expression of its organization's git_host, given the row e
ORGANIZATION_HOST = {
    'repository': '(SELECT git_host_id FROM gnrgh.gnrgh_organization WHERE id=e.organization_id)',
    'issue': '(SELECT git_host_id FROM gnrgh.gnrgh_repository WHERE id=e.repository_id)',
    'pull_request': '(SELECT git_host_id FROM gnrgh.gnrgh_repository WHERE id=e.repository_id)',
    'issue_comment': '(SELECT git_host_id FROM gnrgh.gnrgh_issue WHERE id=e.issue_id)',
    'gh_repo_label': '(SELECT git_host_id FROM gnrgh.gnrgh_repository WHERE id=e.repository_id)',
    'gh_artifact': '(SELECT git_host_id FROM gnrgh.gnrgh_organization WHERE id=e.organization_id)',
    'gh_artifact_version': '(SELECT git_host_id FROM gnrgh.gnrgh_gh_artifact WHERE id=e.artifact_id)',
}

# (table, column pointing to gh_user) with the git_host of the pointing row
GH_USER_REFERENCES = """
    SELECT author_id AS user_id, git_host_id FROM gnrgh.gnrgh_issue
    UNION SELECT author_id, git_host_id FROM gnrgh.gnrgh_pull_request
    UNION SELECT author_id, git_host_id FROM gnrgh.gnrgh_issue_comment
    UNION SELECT owner_id, git_host_id FROM gnrgh.gnrgh_gh_artifact
    UNION SELECT org_user_id, git_host_id FROM gnrgh.gnrgh_organization
    UNION SELECT c.gh_user_id,
                 COALESCE((SELECT git_host_id FROM gnrgh.gnrgh_organization WHERE id=c.organization_id),
                          (SELECT git_host_id FROM gnrgh.gnrgh_repository WHERE id=c.repository_id),
                          (SELECT git_host_id FROM gnrgh.gnrgh_issue WHERE id=c.issue_id),
                          (SELECT git_host_id FROM gnrgh.gnrgh_pull_request WHERE id=c.pull_request_id))
          FROM gnrgh.gnrgh_gh_user_connection c
"""

# first <id> inside <issue> / <pull_request> of a Bag XML payload: the object's
# own id comes before any nested object (user, repository, ...)
ISSUE_ID_RE = r'<issue>(?:[^<]|<(?!id[ >]))*<id[^>]*>(\d+)</id>'
PULL_REQUEST_ID_RE = r'<pull_request>(?:[^<]|<(?!id[ >]))*<id[^>]*>(\d+)</id>'


def column_exists(db, schema, table, column):
    return bool(db.execute(
        """SELECT 1 FROM information_schema.columns
           WHERE table_schema=:s AND table_name=:t AND column_name=:c""",
        sqlargs=dict(s=schema, t=table, c=column)).fetchall())


def main(db):
    git_host_tbl = db.table('gnrgh.git_host')
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
    for api_url, host_id in host_by_url.items():
        db.execute("""UPDATE gnrgh.gnrgh_organization SET git_host_id=:h
                      WHERE git_host_id IS NULL AND api_url=:u""", sqlargs=dict(h=host_id, u=api_url))
    db.execute('UPDATE gnrgh.gnrgh_organization SET git_host_id=:h WHERE git_host_id IS NULL',
               sqlargs=dict(h=github_host_id))

    # 3. imported tables: the host of their organization
    for table, host_sql in ORGANIZATION_HOST.items():
        print(f'\t {table}.git_host_id')
        db.execute(f"""UPDATE gnrgh.gnrgh_{table} e SET git_host_id={host_sql}
                       WHERE e.git_host_id IS NULL""")

    # 4. gh_user: the host of the rows that reference it
    print('\t gh_user.git_host_id')
    db.execute(f"""WITH hosts AS (
                       SELECT user_id, MIN(git_host_id) AS host_id, COUNT(DISTINCT git_host_id) AS n
                       FROM ({GH_USER_REFERENCES}) refs
                       WHERE user_id IS NOT NULL AND git_host_id IS NOT NULL GROUP BY user_id)
                   UPDATE gnrgh.gnrgh_gh_user u SET git_host_id=hosts.host_id
                   FROM hosts WHERE u.id=hosts.user_id AND hosts.n=1 AND u.git_host_id IS NULL""")
    collided = [r[0] for r in db.execute(f"""
                   SELECT user_id FROM ({GH_USER_REFERENCES}) refs
                   WHERE user_id IS NOT NULL AND git_host_id IS NOT NULL
                   GROUP BY user_id HAVING COUNT(DISTINCT git_host_id) > 1""").fetchall()]
    # an account referenced from two servers (the issues of a repository
    # migrated to the hub keep their GitHub authors) belongs to the server of
    # its profile page: html_url starts with the web url of its host
    unresolved = []
    for user_id in collided:
        html_url = user_tbl.readColumns(pkey=user_id, columns='$html_url') or ''
        hosts = [host_id for host_id in git_host_tbl.query(columns='$id').fetchAsDict('id')
                 if html_url.startswith(git_host_tbl.webUrl(host_id) + '/')]
        if len(hosts) == 1:
            user_tbl.batchUpdate(dict(git_host_id=hosts[0]), pkey=user_id)
        else:
            unresolved.append(user_id)
    # accounts nobody references were imported from github.com, the only server
    # that created gh_user rows before git_host existed
    where = 'git_host_id IS NULL'
    if unresolved:
        where += ' AND id NOT IN :unresolved'
    db.execute(f'UPDATE gnrgh.gnrgh_gh_user SET git_host_id=:h WHERE {where}',
               sqlargs=dict(h=github_host_id, unresolved=unresolved))
    for user_id in unresolved:
        login, github_id = user_tbl.readColumns(pkey=user_id, columns='$login,$github_id')
        print(f'\t   gh_user {user_id} ({login}, id {github_id}) is referenced from more than one '
              f'server and its html_url matches none: git_host_id left empty, fix by hand')

    # 5. gh_user.adm_user_id from the old adm.user.gh_user_id
    if column_exists(db, 'adm', 'adm_user', 'gh_user_id'):
        print('\t gh_user.adm_user_id')
        db.execute("""UPDATE gnrgh.gnrgh_gh_user u SET adm_user_id=a.id
                      FROM adm.adm_user a WHERE a.gh_user_id=u.id AND u.adm_user_id IS NULL""")

    # 6. webhook_event: host and linked rows from the payload
    print('\t webhook_event.git_host_id, issue_id, pull_request_id')
    db.execute("""WITH todo AS (
                      SELECT e.id,
                             COALESCE((SELECT git_host_id FROM gnrgh.gnrgh_organization WHERE id=e.organization_id),
                                      (SELECT git_host_id FROM gnrgh.gnrgh_repository WHERE id=e.repo_id),
                                      :github) AS host_id,
                             SUBSTRING(e.payload FROM :issue_re)::bigint AS issue_github_id,
                             SUBSTRING(e.payload FROM :pr_re)::bigint AS pr_github_id
                      FROM gnrgh.gnrgh_webhook_event e WHERE e.git_host_id IS NULL)
                  UPDATE gnrgh.gnrgh_webhook_event e
                  SET git_host_id=todo.host_id,
                      issue_id=(SELECT id FROM gnrgh.gnrgh_issue i
                                WHERE i.git_host_id=todo.host_id AND i.github_id=todo.issue_github_id),
                      pull_request_id=(SELECT id FROM gnrgh.gnrgh_pull_request p
                                       WHERE p.git_host_id=todo.host_id AND p.github_id=todo.pr_github_id)
                  FROM todo WHERE e.id=todo.id""",
               sqlargs=dict(github=github_host_id, issue_re=ISSUE_ID_RE, pr_re=PULL_REQUEST_ID_RE))

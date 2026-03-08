#!/usr/bin/env python
# encoding: utf-8

import os
from datetime import datetime, timezone


class GitHandler(object):
    """Manages git operations on local repository clones.

    Three logical groups of operations:

    ACTIONS — modify the local clone state:
        clone, pull, switch_branch, commit_and_push, diff

    ALIGNMENT — sync DB state with filesystem reality:
        refresh_clone_status, check_all_clones, discover_local_clones

    SYNC — fetch data from GitHub API into DB:
        discover_repositories, refresh_push_status
    """

    def __init__(self, db):
        self.db = db

    @property
    def git_local(self):
        return self.db.package('gnrgh').getGitLocal()

    @property
    def repo_tbl(self):
        return self.db.table('gnrgh.repository')

    def _read_repo(self, repository_id):
        return self.repo_tbl.record(repository_id).output('dict')

    # ── ACTIONS ─────────────────────────────────────────────────

    def clone(self, repository_id):
        """Clone or fetch a repository locally and update tracking fields."""
        rec = self._read_repo(repository_id)
        repo_name = rec['full_name']
        html_url = rec['html_url']
        branch = rec['default_branch'] or 'main'

        repo_path = self.git_local.clone_or_fetch(html_url, repo_name,
                                                   branch=branch)
        commit_sha = self.git_local.get_current_commit(repo_name)
        current_branch = self.git_local.current_branch(repo_name)

        with self.repo_tbl.recordToUpdate(pkey=repository_id) as r:
            r['clone_path'] = repo_path
            r['local_head_sha'] = commit_sha
            r['local_branch'] = current_branch
            r['last_pull_ts'] = datetime.now(timezone.utc)
        return repo_path

    def pull(self, repository_id):
        """Pull latest changes for a cloned repository."""
        rec = self._read_repo(repository_id)
        repo_name = rec['full_name']
        branch = rec['local_branch'] or rec['default_branch'] or 'main'

        self.git_local.pull(repo_name, branch)
        commit_sha = self.git_local.get_current_commit(repo_name)

        with self.repo_tbl.recordToUpdate(pkey=repository_id) as r:
            r['local_head_sha'] = commit_sha
            r['last_pull_ts'] = datetime.now(timezone.utc)
        return commit_sha

    def switch_branch(self, repository_id, branch):
        """Switch the local clone to a different branch."""
        rec = self._read_repo(repository_id)
        repo_name = rec['full_name']

        self.git_local.switch_branch(repo_name, branch)
        commit_sha = self.git_local.get_current_commit(repo_name)

        with self.repo_tbl.recordToUpdate(pkey=repository_id) as r:
            r['local_branch'] = branch
            r['local_head_sha'] = commit_sha

    def diff(self, repository_id):
        """Get diff of local uncommitted changes."""
        rec = self._read_repo(repository_id)
        return self.git_local.diff(rec['full_name'])

    def commit_and_push(self, repository_id, message,
                        author_name=None, author_email=None):
        """Commit local changes and push to remote."""
        rec = self._read_repo(repository_id)
        repo_name = rec['full_name']
        branch = rec['local_branch'] or rec['default_branch'] or 'main'

        self.git_local.commit(repo_name, message,
                              author_name=author_name,
                              author_email=author_email)
        self.git_local.push(repo_name, branch)
        commit_sha = self.git_local.get_current_commit(repo_name)

        with self.repo_tbl.recordToUpdate(pkey=repository_id) as r:
            r['local_head_sha'] = commit_sha
            r['last_pull_ts'] = datetime.now(timezone.utc)

    # ── ALIGNMENT ───────────────────────────────────────────────

    def refresh_clone_status(self, repository_id):
        """Check filesystem and update clone tracking fields for one repo."""
        rec = self._read_repo(repository_id)
        repo_name = rec['full_name']

        if not repo_name or not self.git_local.is_cloned(repo_name):
            with self.repo_tbl.recordToUpdate(pkey=repository_id) as r:
                r['clone_path'] = None
                r['local_head_sha'] = None
                r['local_branch'] = None
                r['last_pull_ts'] = None
            return

        commit_sha = self.git_local.get_current_commit(repo_name)
        current_branch = self.git_local.current_branch(repo_name)
        commit_ts = self.git_local.get_commit_timestamp(repo_name)
        repo_path = self.git_local.repo_path(repo_name)

        with self.repo_tbl.recordToUpdate(pkey=repository_id) as r:
            r['clone_path'] = repo_path
            r['local_head_sha'] = commit_sha
            r['local_branch'] = current_branch
            if commit_ts:
                r['last_pull_ts'] = commit_ts

    def check_all_clones(self):
        """Scan the clone directory and align DB with filesystem.

        For every repository in the DB:
        - if a local clone exists, update clone_path, SHA, branch
        - if no clone exists, clear clone tracking fields

        Returns a summary dict with counts.
        """
        rows = self.repo_tbl.query(
            columns='$id,$full_name',
            order_by='$full_name'
        ).fetch()

        found = 0
        cleared = 0
        for row in rows:
            repo_name = row['full_name']
            if not repo_name:
                continue
            if self.git_local.is_cloned(repo_name):
                self.refresh_clone_status(row['id'])
                found += 1
            else:
                with self.repo_tbl.recordToUpdate(pkey=row['id']) as r:
                    r['clone_path'] = None
                    r['local_head_sha'] = None
                    r['local_branch'] = None
                    r['last_pull_ts'] = None
                cleared += 1

        return dict(found=found, cleared=cleared, total=len(rows))

    # ── SYNC ─────────────────────────────────────────────────────

    def discover_repositories(self, thermo_cb=None):
        """Query GitHub API for each organization and create/update repository records.

        Args:
            thermo_cb: optional callback(items, line_code, message) for progress.
                       Must return an iterable wrapping items. If None, items
                       are iterated directly.
        """
        service = self.db.package('gnrgh').getGithubClient()
        org_tbl = self.db.table('gnrgh.organization')
        orgs = org_tbl.query(
            columns='$id,$login',
            order_by='$login'
        ).fetch()

        wrap = thermo_cb or (lambda items, **kw: items)

        for org_row in wrap(orgs, line_code='orgs',
                            message=lambda item, *args, **kw: item['login']):
            org_login = org_row['login']
            organization_id = org_row['id']
            repos = list(service.getRepositories(organization=org_login))
            for repo_data in wrap(repos, line_code='repos',
                                  message=lambda item, *args, **kw: item.get('name', '')):
                self.repo_tbl.importRepository(repo_data, organization_id=organization_id)
            self.db.commit()

    def refresh_push_status(self, thermo_cb=None):
        """Fetch pushed_at from GitHub API for all repositories and update records.

        Args:
            thermo_cb: optional callback(items, line_code, message) for progress.
        """
        from gnr.core.gnrbag import Bag
        from dateutil.parser import parse as parse_date

        service = self.db.package('gnrgh').getGithubClient()
        orgs = self.db.query('gnrgh.organization',
                             columns='$id,$login').fetch()

        wrap = thermo_cb or (lambda items, **kw: items)

        for org_row in wrap(orgs, line_code='orgs', message='!![en]Organizations'):
            org_login = org_row['login']
            repos = list(service.getRepositories(organization=org_login))
            for repo_data in wrap(repos, line_code='repos', message='!![en]Repositories'):
                github_id = repo_data.get('id')
                if not github_id:
                    continue
                existing = self.repo_tbl.query(
                    where='$github_id=:gid',
                    gid=github_id,
                    columns='$id'
                ).fetch()
                if not existing:
                    continue
                repo_id = existing[0]['id']
                with self.repo_tbl.recordToUpdate(pkey=repo_id) as rec:
                    pushed_at = repo_data.get('pushed_at')
                    if pushed_at and isinstance(pushed_at, str):
                        pushed_at = parse_date(pushed_at)
                    rec['pushed_at'] = pushed_at
                    rec['metadata'] = Bag(repo_data)
            self.db.commit()

    def discover_local_clones(self):
        """Scan the clone directory and list clones not yet in DB.

        Returns list of full_name strings found on disk but missing
        from the repository table.
        """
        base_path = self.git_local.clone_base_path
        known = set()
        rows = self.repo_tbl.query(columns='$full_name').fetch()
        for row in rows:
            if row['full_name']:
                known.add(row['full_name'])

        orphans = []
        if not os.path.isdir(base_path):
            return orphans

        for org_name in sorted(os.listdir(base_path)):
            org_path = os.path.join(base_path, org_name)
            if not os.path.isdir(org_path) or org_name.startswith('.'):
                continue
            for repo_name in sorted(os.listdir(org_path)):
                repo_path = os.path.join(org_path, repo_name)
                if not os.path.isdir(os.path.join(repo_path, '.git')):
                    continue
                full_name = '%s/%s' % (org_name, repo_name)
                if full_name not in known:
                    orphans.append(full_name)
        return orphans

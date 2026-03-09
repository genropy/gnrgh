#!/usr/bin/env python
# encoding: utf-8

import os
import re
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta


class GitHandler(object):
    """Manages git operations on local repository clones.

    Three logical groups of operations:

    ACTIONS — modify the local clone state:
        clone, pull, switch_branch, commit_and_push, diff

    ALIGNMENT — sync DB state with filesystem reality:
        refresh_clone_status

    SYNC — fetch data from GitHub API into DB:
        check_repo, sync_repo, update_clone
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

    def _classify_repo(self, full_name, repo_path):
        """Classify a repository into a repo_group based on name and content."""
        if full_name == 'genropy/genropy':
            return 'framework'
        repo_name = full_name.split('/', 1)[-1]
        if repo_name.startswith('genro-'):
            return 'genro_ng'
        if os.path.isdir(os.path.join(repo_path, 'packages')):
            return 'genropy_app'
        return 'other'

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
            if not r.get('repo_group'):
                r['repo_group'] = self._classify_repo(rec['full_name'], repo_path)
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

    # ── SYNC ─────────────────────────────────────────────────────

    def check_repo(self, organization_id=None, thermo_cb=None):
        """Check repositories: sync from GitHub API, update pushed_at, verify local clones.

        For each repository also checks if a local clone exists and updates
        clone tracking fields (clone_path, local_head_sha, local_branch).

        Args:
            organization_id: optional organization pkey to filter. If None, all orgs.
            thermo_cb: optional callback(items, line_code, message) for progress.
                       Must return an iterable wrapping items. If None, items
                       are iterated directly.
        """
        service = self.db.package('gnrgh').getGithubClient()
        org_tbl = self.db.table('gnrgh.organization')
        if organization_id:
            orgs = org_tbl.query(
                where='$id=:oid', oid=organization_id,
                columns='$id,$login'
            ).fetch()
        else:
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
                repository_id = self.repo_tbl.importRepository(repo_data, organization_id=organization_id)
                self.refresh_clone_status(repository_id)
            self.db.commit()

    def sync_repo(self, pkeys, thermo_cb=None):
        """Sync branches, commits, issues, PRs, topics, labels from GitHub.

        Args:
            pkeys: list of repository pkeys to sync.
            thermo_cb: optional thermo_wrapper callback for progress.
        """
        if not pkeys:
            return
        rows = self.repo_tbl.query(
            where='$id IN :pkeys',
            pkeys=pkeys,
            columns='$id,$full_name,$organization_id'
        ).fetch()
        service = self.db.package('gnrgh').getGithubClient()
        branch_tbl = self.db.table('gnrgh.branch')
        issue_tbl = self.db.table('gnrgh.issue')
        pr_tbl = self.db.table('gnrgh.pull_request')
        topic_link_tbl = self.db.table('gnrgh.gh_topic_link')
        label_tbl = self.db.table('gnrgh.gh_repo_label')
        commit_tbl = self.db.table('gnrgh.commit')
        connection_tbl = self.db.table('gnrgh.gh_user_connection')
        comment_tbl = self.db.table('gnrgh.issue_comment')

        wrap = thermo_cb or (lambda items, **kw: items)

        for row in wrap(rows, line_code='repos',
                        message=lambda item, *args, **kw: item.get('full_name', '')):
            full_name = row.get('full_name')
            repository_id = row['id']
            if not full_name or '/' not in full_name:
                continue
            owner, repo_name = full_name.split('/', 1)

            import_steps = [
                dict(name='Branches'),
                dict(name='Commits'),
                dict(name='Issues'),
                dict(name='Pull Requests'),
                dict(name='Topics & Labels'),
            ]

            for step in wrap(import_steps, line_code='import_type',
                             message=lambda item, *args, **kw: item['name']):
                step_name = step['name']

                if step_name == 'Branches':
                    branches_data = list(service.getBranches(owner=owner, repo=repo_name))
                    for br_data in wrap(branches_data, line_code='detail',
                                        message=lambda item, *args, **kw: item.get('name', '')):
                        branch_tbl.importBranch(br_data, repository_id=repository_id)

                elif step_name == 'Commits':
                    max_count, since_date = self._resolve_commit_policy(
                        organization_id=row.get('organization_id'),
                        repository_id=repository_id)
                    if max_count != 0:
                        kw = {}
                        if since_date:
                            kw['since'] = since_date.isoformat()
                        commits_data = list(service.getCommits(
                            owner=owner, repo=repo_name,
                            per_page=min(max_count or 100, 100),
                            **kw))
                        if max_count and not since_date:
                            commits_data = commits_data[:max_count]
                        for c_data in wrap(commits_data, line_code='detail',
                                           message=lambda item, *args, **kw: item.get('sha', '')[:8]):
                            commit_tbl.importCommit(c_data, repository_id=repository_id)
                        if since_date and len(commits_data) < 5:
                            fallback = list(service.getCommits(
                                owner=owner, repo=repo_name,
                                per_page=5))[:5]
                            for c_data in fallback:
                                commit_tbl.importCommit(c_data, repository_id=repository_id)

                        # Link commits to main branches (master/main, develop/development)
                        key_branches = branch_tbl.query(
                            where="$repository_id=:repo_id AND $name IN :names",
                            repo_id=repository_id,
                            names=['master', 'main', 'develop', 'development'],
                            columns='$id,$name'
                        ).fetch()
                        for br in key_branches:
                            kw_br = {}
                            if since_date:
                                kw_br['since'] = since_date.isoformat()
                            br_commits = list(service.getCommits(
                                owner=owner, repo=repo_name,
                                sha=br['name'],
                                per_page=min(max_count or 100, 100),
                                **kw_br))
                            if max_count and not since_date:
                                br_commits = br_commits[:max_count]
                            for c_data in br_commits:
                                commit_tbl.importCommit(c_data,
                                    repository_id=repository_id,
                                    branch_id=br['id'])
                            if since_date and len(br_commits) < 5:
                                br_fallback = list(service.getCommits(
                                    owner=owner, repo=repo_name,
                                    sha=br['name'],
                                    per_page=5))[:5]
                                for c_data in br_fallback:
                                    commit_tbl.importCommit(c_data,
                                        repository_id=repository_id,
                                        branch_id=br['id'])
                            with branch_tbl.recordToUpdate(pkey=br['id']) as br_rec:
                                br_rec['last_sync_ts'] = datetime.now(timezone.utc)

                elif step_name == 'Issues':
                    issues = list(service.getIssues(owner=owner, repo=repo_name, state='all'))
                    for issue_data in wrap(issues, line_code='detail',
                                           message=lambda item, *args, **kw: '#%s %s' % (
                                               item.get('number', ''), item.get('title', '')[:40])):
                        issue_id = issue_tbl.importIssue(issue_data, repository_id=repository_id)
                        if issue_id and issue_data.get('comments', 0) > 0:
                            comments = service.getIssueComments(
                                owner=owner, repo=repo_name,
                                issue_number=issue_data['number'])
                            comment_tbl.importCommentsForIssue(comments, issue_id=issue_id)

                elif step_name == 'Pull Requests':
                    pull_requests = list(service.getPullRequests(owner=owner, repo=repo_name, state='all'))
                    for pr_data in wrap(pull_requests, line_code='detail',
                                        message=lambda item, *args, **kw: '#%s %s' % (
                                            item.get('number', ''), item.get('title', '')[:40])):
                        pr_tbl.importPullRequest(pr_data, repository_id=repository_id)

                elif step_name == 'Topics & Labels':
                    topics = service.getRepositoryTopics(owner=owner, repo=repo_name)
                    topic_link_tbl.syncTopics(topics, repository_id=repository_id)
                    labels = service.getRepositoryLabels(owner=owner, repo=repo_name)
                    label_tbl.syncLabels(labels, repository_id=repository_id)
                    connection_tbl.syncMembersFromTopics(repository_id=repository_id)

            with self.repo_tbl.recordToUpdate(pkey=repository_id) as rec:
                rec['last_sync_ts'] = datetime.now(timezone.utc)

            self.db.commit()

    def update_clone(self, pkeys, thermo_cb=None):
        """Clone or pull selected repositories.

        Args:
            pkeys: list of repository pkeys.
            thermo_cb: optional thermo_wrapper callback for progress.
        """
        if not pkeys:
            return
        rows = self.repo_tbl.query(
            where='$id IN :pkeys',
            pkeys=pkeys,
            columns='$id,$full_name,$clone_path'
        ).fetch()

        wrap = thermo_cb or (lambda items, **kw: items)

        for row in wrap(rows, line_code='repos',
                        message=lambda item, *args, **kw: item.get('full_name', '')):
            try:
                if row['clone_path']:
                    self.pull(row['id'])
                else:
                    self.clone(row['id'])
                self.db.commit()
            except Exception:
                self.db.rollback()

    def _resolve_commit_policy(self, organization_id=None, repository_id=None, branch_id=None):
        """Resolve commit_policy following hierarchy: branch > repo > org > preference."""
        if branch_id:
            rec = self.db.table('gnrgh.branch').record(branch_id).output('dict')
            if rec.get('commit_policy'):
                return self._parse_policy(rec['commit_policy'])
        if repository_id:
            rec = self.repo_tbl.record(repository_id).output('dict')
            if rec.get('commit_policy'):
                return self._parse_policy(rec['commit_policy'])
        if organization_id:
            rec = self.db.table('gnrgh.organization').record(organization_id).output('dict')
            if rec.get('commit_policy'):
                return self._parse_policy(rec['commit_policy'])
        default_policy = self.db.application.getPreference('commit_policy', pkg='gnrgh') or '5'
        return self._parse_policy(default_policy)

    def _parse_policy(self, policy_str):
        """Parse a commit_policy string."""
        policy_str = policy_str.strip()
        match = re.match(r'^(\d+)\s*[mM]$', policy_str)
        if match:
            months = int(match.group(1))
            if months == 0:
                return (0, None)
            since = datetime.now(timezone.utc) - relativedelta(months=months)
            return (None, since)
        try:
            n = int(policy_str)
            return (n, None)
        except ValueError:
            return (5, None)

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

# -*- coding: utf-8 -*-

import re
from datetime import datetime
from dateutil.relativedelta import relativedelta
from gnr.web.batch.btcaction import BaseResourceAction

caption = 'Deep Sync Repositories'
description = 'Sync branches, commits, issues, PRs, topics, labels and collaborators for selected repositories'

class Main(BaseResourceAction):
    batch_prefix = 'DEEP_SYNC'
    batch_title = caption
    batch_selection_savedQuery = False

    def do(self):
        pkeys = self.get_selection_pkeys()
        if not pkeys:
            return
        rows = self.tblobj.query(
            where='$id IN :pkeys',
            pkeys=pkeys,
            columns='$id,$full_name,$organization_id'
        ).fetch()
        github_service = self.db.package('gnrgh').getGithubClient()
        branch_tbl = self.db.table('gnrgh.branch')
        issue_tbl = self.db.table('gnrgh.issue')
        pr_tbl = self.db.table('gnrgh.pull_request')
        topic_link_tbl = self.db.table('gnrgh.gh_topic_link')
        label_tbl = self.db.table('gnrgh.gh_repo_label')
        commit_tbl = self.db.table('gnrgh.commit')
        connection_tbl = self.db.table('gnrgh.gh_user_connection')
        comment_tbl = self.db.table('gnrgh.issue_comment')

        for row in self.btc.thermo_wrapper(rows, line_code='repos', message='!![en]Repositories'):
            full_name = row.get('full_name')
            repository_id = row['id']
            if not full_name or '/' not in full_name:
                continue
            owner, repo_name = full_name.split('/', 1)

            branches_data = github_service.getBranches(owner=owner, repo=repo_name)
            branch_tbl.importBranches(branches_data, repository_id=repository_id)

            # Commits
            max_count, since_date = self._resolve_commit_policy(
                organization_id=row.get('organization_id'),
                repository_id=repository_id)
            if max_count != 0:
                kw = {}
                if since_date:
                    kw['since'] = since_date.isoformat()
                commits_data = github_service.getCommits(
                    owner=owner, repo=repo_name,
                    per_page=min(max_count or 100, 100),
                    paginate=since_date is not None,
                    **kw)
                if max_count and not since_date:
                    commits_data = list(commits_data)[:max_count]
                n_imported = commit_tbl.importCommits(commits_data, repository_id=repository_id)
                if since_date and n_imported < 5:
                    fallback = github_service.getCommits(
                        owner=owner, repo=repo_name,
                        per_page=5, paginate=False)
                    commit_tbl.importCommits(list(fallback)[:5],
                        repository_id=repository_id)

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
                    br_commits = github_service.getCommits(
                        owner=owner, repo=repo_name,
                        sha=br['name'],
                        per_page=min(max_count or 100, 100),
                        paginate=since_date is not None,
                        **kw_br)
                    if max_count and not since_date:
                        br_commits = list(br_commits)[:max_count]
                    n_br_imported = commit_tbl.importCommits(br_commits,
                        repository_id=repository_id,
                        branch_id=br['id'])
                    if since_date and n_br_imported < 5:
                        br_fallback = github_service.getCommits(
                            owner=owner, repo=repo_name,
                            sha=br['name'],
                            per_page=5, paginate=False)
                        commit_tbl.importCommits(list(br_fallback)[:5],
                            repository_id=repository_id,
                            branch_id=br['id'])
                    with branch_tbl.recordToUpdate(pkey=br['id']) as br_rec:
                        br_rec['last_sync_ts'] = datetime.now()

            issues = github_service.getIssues(owner=owner, repo=repo_name, state='all')
            for issue_data in self.btc.thermo_wrapper(issues, line_code='detail', message='!![en]Issues'):
                issue_id = issue_tbl.importIssue(issue_data, repository_id=repository_id)
                if issue_id and issue_data.get('comments', 0) > 0:
                    comments = github_service.getIssueComments(
                        owner=owner, repo=repo_name,
                        issue_number=issue_data['number'])
                    comment_tbl.importCommentsForIssue(comments, issue_id=issue_id)

            pull_requests = github_service.getPullRequests(owner=owner, repo=repo_name, state='all')
            for pr_data in self.btc.thermo_wrapper(pull_requests, line_code='detail', message='!![en]Pull Requests'):
                pr_tbl.importPullRequest(pr_data, repository_id=repository_id)

            topics = github_service.getRepositoryTopics(owner=owner, repo=repo_name)
            topic_link_tbl.syncTopics(topics, repository_id=repository_id)

            labels = github_service.getRepositoryLabels(owner=owner, repo=repo_name)
            label_tbl.syncLabels(labels, repository_id=repository_id)

            connection_tbl.syncMembersFromTopics(repository_id=repository_id)

            with self.tblobj.recordToUpdate(pkey=repository_id) as rec:
                rec['last_sync_ts'] = datetime.now()

            self.db.commit()

    def _resolve_commit_policy(self, organization_id=None, repository_id=None, branch_id=None):
        """Resolve commit_policy following hierarchy: branch > repo > org > preference."""
        # Check branch level
        if branch_id:
            rec = self.db.table('gnrgh.branch').record(branch_id).output('dict')
            if rec.get('commit_policy'):
                return self._parse_policy(rec['commit_policy'])
        # Check repo level
        if repository_id:
            rec = self.db.table('gnrgh.repository').record(repository_id).output('dict')
            if rec.get('commit_policy'):
                return self._parse_policy(rec['commit_policy'])
        # Check organization level
        if organization_id:
            rec = self.db.table('gnrgh.organization').record(organization_id).output('dict')
            if rec.get('commit_policy'):
                return self._parse_policy(rec['commit_policy'])
        # Default from preferences
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
            since = datetime.now() - relativedelta(months=months)
            return (None, since)
        try:
            n = int(policy_str)
            return (n, None)
        except ValueError:
            return (5, None)

    batch_dialog_width = '400px'

    def table_script_parameters_pane(self, pane, record_count=None, **kwargs):
        pane.div('Deep sync for <b>%s</b> selected repositories.' % (record_count or 0),
                 style='margin:10px;padding:10px;background:#fff3cd;border-radius:4px;'
                        'word-wrap:break-word;')
        pane.div('Will import: branches, commits, issues, pull requests, topics, labels, collaborators.',
                 style='margin:10px;font-size:12px;color:#666;')

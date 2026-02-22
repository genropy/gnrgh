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
        commit_tbl = self.db.table('gnrgh.commit')
        issue_tbl = self.db.table('gnrgh.issue')
        pr_tbl = self.db.table('gnrgh.pull_request')
        topic_link_tbl = self.db.table('gnrgh.gh_topic_link')
        label_tbl = self.db.table('gnrgh.gh_repo_label')
        connection_tbl = self.db.table('gnrgh.gh_user_connection')

        for row in self.btc.thermo_wrapper(rows, line_code='repos', message='!![en]Repositories'):
            full_name = row.get('full_name')
            repository_id = row['id']
            if not full_name or '/' not in full_name:
                continue
            owner, repo_name = full_name.split('/', 1)

            branches_data = github_service.getBranches(owner=owner, repo=repo_name)
            branch_tbl.importBranches(branches_data, repository_id=repository_id)

            # Import commits for each branch according to policy
            branches = branch_tbl.query(
                where='$repository_id=:repo_id',
                repo_id=repository_id,
                columns='$id,$name'
            ).fetch()
            for br in self.btc.thermo_wrapper(branches, line_code='detail', message='!![en]Branches'):
                limit, since = self._resolve_commit_policy(
                    organization_id=row.get('organization_id'),
                    repository_id=repository_id,
                    branch_id=br['id']
                )
                if limit == 0:
                    continue
                kw = {}
                if since:
                    kw['since'] = since.isoformat()
                commits_data = github_service.getCommits(
                    owner=owner, repo=repo_name,
                    sha=br['name'], per_page=min(limit or 100, 100),
                    paginate=bool(since),
                    **kw
                )
                if limit and not since:
                    commits_data = commits_data[:limit]
                commit_tbl.importCommits(commits_data, branch_id=br['id'])

            issues = github_service.getIssues(owner=owner, repo=repo_name, state='all')
            for issue_data in self.btc.thermo_wrapper(issues, line_code='detail', message='!![en]Issues'):
                issue_tbl.importIssue(issue_data, repository_id=repository_id)

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

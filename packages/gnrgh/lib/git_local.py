#!/usr/bin/env python
# encoding: utf-8

import os
import hashlib
import subprocess


class GitLocal(object):
    """Manages local git clones for gnrgh repositories.

    Handles clone, fetch, pull, status, diff, commit, push
    and branch operations on local repository clones.

    Clone strategy: shallow by default (--depth 1),
    unshallow on-demand when advanced operations require it.
    """

    def __init__(self, clone_base_path):
        self._clone_base_path = clone_base_path

    @property
    def clone_base_path(self):
        return self._clone_base_path

    def repo_path(self, repo_name):
        """Return absolute path for a repo clone."""
        return os.path.join(self.clone_base_path, repo_name)

    def is_cloned(self, repo_name):
        """Check if repo has a local clone."""
        return os.path.isdir(os.path.join(self.repo_path(repo_name), '.git'))

    def is_shallow(self, repo_name):
        """Check if the clone is shallow."""
        return os.path.isfile(
            os.path.join(self.repo_path(repo_name), '.git', 'shallow'))

    def _run(self, args, repo_name, check=True, text=True):
        """Run a git command in the repo directory."""
        return subprocess.run(
            args, cwd=self.repo_path(repo_name),
            check=check, capture_output=True, text=text)

    def _to_ssh_url(self, url):
        """Convert HTTPS GitHub URL to SSH URL."""
        if url.startswith('https://github.com/'):
            path = url.replace('https://github.com/', '')
            if not path.endswith('.git'):
                path = path + '.git'
            return 'git@github.com:%s' % path
        return url

    # --- Clone / Fetch / Pull ---

    def clone_or_fetch(self, repo_url, repo_name, branch='main'):
        """Clone the repo if not present, otherwise fetch and reset to remote.

        Returns the repo local path.
        """
        repo_url = self._to_ssh_url(repo_url)
        repo_path = self.repo_path(repo_name)
        if self.is_cloned(repo_name):
            self._run(['git', 'fetch', 'origin', branch], repo_name)
            self._run(['git', 'checkout', branch], repo_name)
            self._run(['git', 'reset', '--hard', 'origin/%s' % branch],
                       repo_name)
        else:
            os.makedirs(repo_path, exist_ok=True)
            subprocess.run(
                ['git', 'clone', '--depth', '1', '--branch', branch,
                 repo_url, repo_path],
                check=True, capture_output=True)
        return repo_path

    def fetch(self, repo_name):
        """Fetch from origin without modifying working tree."""
        self._run(['git', 'fetch', 'origin'], repo_name)

    def pull(self, repo_name, branch):
        """Fetch and reset working tree to match remote branch."""
        self._run(['git', 'fetch', 'origin', branch], repo_name)
        self._run(['git', 'reset', '--hard', 'origin/%s' % branch],
                   repo_name)

    def unshallow(self, repo_name):
        """Convert shallow clone to full clone."""
        if self.is_shallow(repo_name):
            self._run(['git', 'fetch', '--unshallow'], repo_name)

    # --- Status / Info ---

    def get_current_commit(self, repo_name):
        """Get the HEAD commit hash."""
        result = self._run(['git', 'rev-parse', 'HEAD'], repo_name)
        return result.stdout.strip()

    def get_commit_timestamp(self, repo_name):
        """Get the HEAD commit timestamp as datetime."""
        from datetime import datetime
        result = self._run(
            ['git', 'log', '-1', '--format=%cI'], repo_name)
        ts_str = result.stdout.strip()
        if ts_str:
            return datetime.fromisoformat(ts_str)
        return None

    def current_branch(self, repo_name):
        """Get the name of the currently checked out branch."""
        result = self._run(
            ['git', 'branch', '--show-current'], repo_name)
        return result.stdout.strip()

    def list_branches(self, repo_name):
        """List all branches (local and remote).

        Returns dict(local=[...], remote=[...]).
        """
        result = self._run(['git', 'branch', '-a', '--no-color'], repo_name)
        local = []
        remote = []
        for line in result.stdout.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            if line.startswith('* '):
                line = line[2:]
            if line.startswith('remotes/origin/'):
                branch_name = line.replace('remotes/origin/', '')
                if branch_name != 'HEAD':
                    remote.append(branch_name)
            else:
                local.append(line)
        return dict(local=local, remote=remote)

    def status(self, repo_name):
        """Get working tree status (modified/untracked files).

        Returns list of (status_code, filepath) tuples.
        """
        result = self._run(
            ['git', 'status', '--porcelain'], repo_name)
        files = []
        for line in result.stdout.strip().split('\n'):
            if line:
                files.append((line[:2], line[3:]))
        return files

    def ahead_behind(self, repo_name, branch):
        """Count commits ahead/behind relative to remote branch.

        Returns (ahead, behind) tuple.
        """
        self.fetch(repo_name)
        result = self._run(
            ['git', 'rev-list', '--left-right', '--count',
             'origin/%s...HEAD' % branch],
            repo_name, check=False)
        if result.returncode != 0:
            return (0, 0)
        parts = result.stdout.strip().split('\t')
        if len(parts) == 2:
            return (int(parts[1]), int(parts[0]))
        return (0, 0)

    # --- Diff ---

    def diff(self, repo_name):
        """Get diff of unstaged changes."""
        result = self._run(['git', 'diff'], repo_name)
        return result.stdout

    def diff_staged(self, repo_name):
        """Get diff of staged changes."""
        result = self._run(['git', 'diff', '--staged'], repo_name)
        return result.stdout

    def diff_with_remote(self, repo_name, branch):
        """Get diff between local HEAD and remote branch."""
        self.fetch(repo_name)
        result = self._run(
            ['git', 'diff', 'origin/%s..HEAD' % branch], repo_name)
        return result.stdout

    # --- Branch operations ---

    def switch_branch(self, repo_name, branch):
        """Switch to a different branch. Unshallows if necessary."""
        if self.is_shallow(repo_name):
            self.unshallow(repo_name)
        self.fetch(repo_name)
        # Try local branch first, then create from remote
        result = self._run(
            ['git', 'switch', branch], repo_name, check=False)
        if result.returncode != 0:
            self._run(
                ['git', 'switch', '-c', branch, 'origin/%s' % branch],
                repo_name)

    # --- Commit / Push ---

    def commit(self, repo_name, message, author_name=None, author_email=None):
        """Stage all changes and commit."""
        self._run(['git', 'add', '-A'], repo_name)
        cmd = ['git', 'commit', '-m', message]
        env = None
        if author_name and author_email:
            env = os.environ.copy()
            env['GIT_AUTHOR_NAME'] = author_name
            env['GIT_AUTHOR_EMAIL'] = author_email
            env['GIT_COMMITTER_NAME'] = author_name
            env['GIT_COMMITTER_EMAIL'] = author_email
        subprocess.run(
            cmd, cwd=self.repo_path(repo_name),
            check=True, capture_output=True, text=True, env=env)

    def push(self, repo_name, branch):
        """Push local commits to remote."""
        self._run(['git', 'push', 'origin', branch], repo_name)

    # --- File operations ---

    def list_files(self, repo_name, pattern='*.py'):
        """List files tracked by git matching a pattern."""
        result = self._run(
            ['git', 'ls-files', pattern], repo_name)
        return [f for f in result.stdout.strip().split('\n') if f]

    def list_package_files(self, repo_name, package_path, pattern='*.py'):
        """List files under a specific package path.

        Returns paths relative to the package root.
        """
        result = self._run(
            ['git', 'ls-files', os.path.join(package_path, pattern)],
            repo_name)
        prefix = package_path + '/'
        return [f[len(prefix):] if f.startswith(prefix) else f
                for f in result.stdout.strip().split('\n') if f]

    def get_changed_files(self, repo_name, old_hash, new_hash,
                          path_filter=None):
        """Get list of changed files between two commits."""
        cmd = ['git', 'diff', '--name-only', '--diff-filter=ACMR',
               old_hash, new_hash]
        if path_filter:
            cmd.extend(['--', path_filter])
        result = self._run(cmd, repo_name)
        return [f for f in result.stdout.strip().split('\n') if f]

    def get_deleted_files(self, repo_name, old_hash, new_hash,
                          path_filter=None):
        """Get list of deleted files between two commits."""
        cmd = ['git', 'diff', '--name-only', '--diff-filter=D',
               old_hash, new_hash]
        if path_filter:
            cmd.extend(['--', path_filter])
        result = self._run(cmd, repo_name)
        return [f for f in result.stdout.strip().split('\n') if f]

    def get_changed_package_files(self, repo_name, old_hash, new_hash,
                                  package_path):
        """Get changed files scoped to a package path.

        Returns paths relative to the package root.
        """
        files = self.get_changed_files(
            repo_name, old_hash, new_hash,
            os.path.join(package_path, '*.py'))
        prefix = package_path + '/'
        return [f[len(prefix):] if f.startswith(prefix) else f
                for f in files]

    def get_deleted_package_files(self, repo_name, old_hash, new_hash,
                                  package_path):
        """Get deleted files scoped to a package path.

        Returns paths relative to the package root.
        """
        files = self.get_deleted_files(
            repo_name, old_hash, new_hash,
            os.path.join(package_path, '*.py'))
        prefix = package_path + '/'
        return [f[len(prefix):] if f.startswith(prefix) else f
                for f in files]

    def read_file(self, repo_name, path):
        """Read a file from the local clone. Returns content or None."""
        full_path = os.path.join(self.repo_path(repo_name), path)
        if not os.path.isfile(full_path):
            return None
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()

    @staticmethod
    def content_hash(content):
        """Compute SHA256 hash of content string."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

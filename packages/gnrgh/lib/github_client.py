#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Github Client for GNRGH
#  Standalone GitHub API client (no GnrBaseService dependency)
#
#  Based on original service by Davide Paci (2022-05-13)
#  Copyright (c) 2022 Softwell. All rights reserved.
#

import requests
import json
import subprocess
import logging

logger = logging.getLogger(__name__)

API_URL = "https://api.github.com"
AUTH_API_URL = "https://github.com/login/oauth"


class GithubAuthorizationError(Exception):
    """Exception raised when GitHub API authentication fails.

    Raised for HTTP 401 (Unauthorized) and 403 (Forbidden) responses,
    indicating invalid, expired, or missing access tokens.
    """
    code = 'GHAUTH001'
    description = 'GitHub authorization failed'

    def __init__(self, message=None, status_code=None):
        self.status_code = status_code
        super().__init__(message or self.description)


class GithubNotFoundError(Exception):
    """Exception raised when a GitHub resource is not found.

    Raised for HTTP 404 (Not Found) responses, indicating the requested
    resource (repository, organization, user, etc.) does not exist.
    """
    code = 'GHNOTFOUND001'
    description = 'GitHub resource not found'

    def __init__(self, message=None, status_code=None):
        self.status_code = status_code
        super().__init__(message or self.description)


# Map of HTTP status codes to exception classes that should be raised
# Status codes not in this map will only be logged, not raised
RAISING_ERROR_CODES = {
    401: GithubAuthorizationError,
    403: GithubAuthorizationError,
    404: GithubNotFoundError,
}


class GithubClient(object):
    def __init__(self, access_token=None):
        """Initialize the GitHub client.

        Args:
            access_token: GitHub personal access token. If not provided,
                          will attempt to get token from local gh CLI tool.
        """
        self.access_token = access_token
        if not self.access_token:
            self.access_token = self.get_local_gh_token()

    def get_local_gh_token(self):
        """Get the local GitHub token from the gh CLI tool.

        Returns the token if gh is authenticated, None otherwise.
        """
        try:
            result = subprocess.run(
                ['gh', 'auth', 'token'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

    def _auth_request(self, resource, access_token=None, method="get", **kw):
        access_token = access_token or self.access_token
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        headers.update(kw.pop("headers", {}))
        url = resource if resource.startswith("http") else f"{API_URL}{resource}"
        r = getattr(requests, method)(url, headers=headers, **kw)
        return r

    def _handle_error(self, response, operation):
        """Log error and raise exception for critical status codes.

        Always logs the error. Raises an exception only if the status code
        is in RAISING_ERROR_CODES (see module level constant for the mapping).

        Args:
            response: The HTTP response object
            operation: Name of the operation that failed (for logging)
        """
        error_msg = f"GitHub API error ({operation}): HTTP {response.status_code}"
        try:
            error_data = response.json()
            if 'message' in error_data:
                error_msg = f"{error_msg} - {error_data['message']}"
        except (ValueError, KeyError):
            error_msg = f"{error_msg} - {response.content.decode('utf-8', errors='ignore')}"

        logger.error(error_msg)

        exception_class = RAISING_ERROR_CODES.get(response.status_code)
        if exception_class:
            raise exception_class(error_msg, status_code=response.status_code)

    def getWorkspaces(self, access_token=None, **kwargs):
        "Returns organization ID"
        r = self._auth_request("/user/orgs", access_token)
        if not r.ok:
            self._handle_error(r, 'getWorkspaces')
            return []
        return r.json()

    def getUser(self, access_token=None, **kwargs):
        "Returns user data"
        r = self._auth_request("/user", access_token)
        if not r.ok:
            self._handle_error(r, 'getUser')
            return None
        return r.json()

    def getOrganization(self, organization=None, access_token=None, **kwargs):
        """Returns organization data by login name.

        Args:
            organization: Organization login name
            access_token: GitHub access token (optional, uses self.access_token if not provided)

        Returns:
            dict with organization data or None if error

        Raises:
            GithubAuthorizationError: If authentication fails
        """
        if not organization:
            return None

        endpoint = f"/orgs/{organization}"
        r = self._auth_request(endpoint, access_token)

        if not r.ok:
            self._handle_error(r, 'getOrganization')
            return None

        return r.json()

    def getRepository(self, organization=None, name=None, github_id=None, access_token=None, **kwargs):
        """Returns a single repository data.

        Args:
            organization: Organization login name (required if using name)
            name: Repository name (requires organization)
            github_id: GitHub repository ID (alternative to organization+name)
            access_token: GitHub access token (optional, uses self.access_token if not provided)

        Returns:
            dict with repository data or None if error

        Raises:
            GithubAuthorizationError: If authentication fails
        """
        if github_id:
            endpoint = f"/repositories/{github_id}"
        elif organization and name:
            endpoint = f"/repos/{organization}/{name}"
        else:
            return None

        r = self._auth_request(endpoint, access_token)

        if not r.ok:
            self._handle_error(r, 'getRepository')
            return None

        return r.json()

    def getRepositories(
        self, access_token=None, organization=None, per_page=100, **kwargs
    ):
        "Get All Github repositories in an organization or user"
        params = {"per_page": per_page, **kwargs}

        if organization:
            endpoint = f"/orgs/{organization}/repos"
        else:
            endpoint = "/user/repos"

        r = self._auth_request(endpoint, access_token, params=params)

        if not r.ok:
            self._handle_error(r, 'getRepositories')
            return []

        repositories = r.json()
        if self._extractPaginationLink(r.headers.get("Link"), rel="next"):
            self._paginatedResults(
                endpoint,
                access_token=access_token,
                params=params,
                result_list=repositories,
            )

        return repositories

    def getProjects(self, access_token=None, organization=None, per_page=100, **kwargs):
        "Get All Github projects in an organization"
        params = {"per_page": per_page, **kwargs}

        if not organization:
            return []

        endpoint = f"/orgs/{organization}/projects"

        r = self._auth_request(endpoint, access_token, params=params)

        if not r.ok:
            self._handle_error(r, 'getProjects')
            return []

        projects = r.json()
        if self._extractPaginationLink(r.headers.get("Link"), rel="next"):
            self._paginatedResults(
                endpoint, access_token=access_token, params=params, result_list=projects
            )

        return projects

    def getIssues(
        self,
        access_token=None,
        owner=None,
        repo=None,
        per_page=100,
        state="open",
        assignee="*",
        since=None,
        **kwargs,
    ):
        """Get All Github issues in a repository.
        State: can be 'open', 'closed', 'all'
        Assignee: can be '*' (anyone), 'none' (not assigned), username
        Since: timestamp in ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ
        """
        params = {
            "per_page": per_page,
            state: state,
            assignee: assignee,
            since: since,
            **kwargs,
        }

        if not owner or not repo:
            return []
        endpoint = f"/repos/{owner}/{repo}/issues"

        r = self._auth_request(endpoint, access_token, params=params)

        if not r.ok:
            self._handle_error(r, 'getIssues')
            return []

        issues = r.json()
        if self._extractPaginationLink(r.headers.get("Link"), rel="next"):
            self._paginatedResults(
                endpoint, access_token=access_token, params=params, result_list=issues
            )

        return issues

    def getIssueComments(
        self,
        access_token=None,
        owner=None,
        repo=None,
        issue_number=None,
        per_page=100,
        since=None,
        **kwargs,
    ):
        """Get all comments for a specific issue.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number
            per_page: Results per page (max 100)
            since: Only comments updated after this timestamp (ISO 8601)
        """
        if not owner or not repo or not issue_number:
            return []

        params = {"per_page": per_page}
        if since:
            params["since"] = since

        endpoint = f"/repos/{owner}/{repo}/issues/{issue_number}/comments"

        r = self._auth_request(endpoint, access_token, params=params)

        if not r.ok:
            self._handle_error(r, 'getIssueComments')
            return []

        comments = r.json()
        if self._extractPaginationLink(r.headers.get("Link"), rel="next"):
            self._paginatedResults(
                endpoint, access_token=access_token, params=params, result_list=comments
            )

        return comments

    def createIssue(
        self,
        access_token=None,
        owner=None,
        repo=None,
        title=None,
        body=None,
        assignees=None,
        labels=None,
        milestone=None,
        **kwargs,
    ):
        """Create an issue in a repository.

        Args:
            owner: Repository owner (org or user)
            repo: Repository name
            title: Issue title (required)
            body: Issue body/description
            assignees: List of usernames to assign
            labels: List of label names
            milestone: Milestone number

        Returns:
            dict with created issue data or None if error

        Raises:
            GithubAuthorizationError: If authentication fails
        """
        if not owner or not repo or not title:
            return None

        endpoint = f"/repos/{owner}/{repo}/issues"

        data = {"title": title}
        if body:
            data["body"] = body
        if assignees:
            data["assignees"] = assignees if isinstance(assignees, list) else [assignees]
        if labels:
            data["labels"] = labels if isinstance(labels, list) else [labels]
        if milestone:
            data["milestone"] = milestone

        r = self._auth_request(endpoint, access_token, method="post", json=data)

        if not r.ok:
            self._handle_error(r, 'createIssue')
            return None

        return r.json()

    def getPullRequests(
        self,
        access_token=None,
        owner=None,
        repo=None,
        per_page=100,
        state="open",
        sort="created",
        direction="desc",
        **kwargs,
    ):
        """Get pull requests for a repository.

        Args:
            owner: Repository owner (org or user)
            repo: Repository name
            state: 'open', 'closed', 'all'
            sort: 'created', 'updated', 'popularity', 'long-running'
            direction: 'asc', 'desc'

        Returns:
            List of pull request dicts from GitHub API
        """
        params = {
            "per_page": per_page,
            "state": state,
            "sort": sort,
            "direction": direction,
            **kwargs,
        }

        if not owner or not repo:
            return []

        endpoint = f"/repos/{owner}/{repo}/pulls"

        r = self._auth_request(endpoint, access_token, params=params)

        if not r.ok:
            self._handle_error(r, 'getPullRequests')
            return []

        pull_requests = r.json()
        if self._extractPaginationLink(r.headers.get("Link"), rel="next"):
            self._paginatedResults(
                endpoint, access_token=access_token, params=params, result_list=pull_requests
            )

        return pull_requests

    def getOrgMembers(
        self,
        access_token=None,
        organization=None,
        per_page=100,
        role="all",
        **kwargs,
    ):
        """Get members of an organization.

        Args:
            organization: Organization login name
            role: 'all', 'admin', 'member'

        Returns:
            List of user dicts from GitHub API
        """
        params = {
            "per_page": per_page,
            "role": role,
            **kwargs,
        }

        if not organization:
            return []

        endpoint = f"/orgs/{organization}/members"

        r = self._auth_request(endpoint, access_token, params=params)

        if not r.ok:
            self._handle_error(r, 'getOrgMembers')
            return []

        members = r.json()
        if self._extractPaginationLink(r.headers.get("Link"), rel="next"):
            self._paginatedResults(
                endpoint, access_token=access_token, params=params, result_list=members
            )

        return members

    def getRepoCollaborators(
        self,
        access_token=None,
        owner=None,
        repo=None,
        per_page=100,
        **kwargs,
    ):
        """Get collaborators of a repository.

        Args:
            owner: Repository owner (org or user)
            repo: Repository name

        Returns:
            List of user dicts from GitHub API

        Raises:
            GithubAuthorizationError: If authentication fails
        """
        params = {
            "per_page": per_page,
            **kwargs,
        }

        if not owner or not repo:
            return []

        endpoint = f"/repos/{owner}/{repo}/collaborators"

        r = self._auth_request(endpoint, access_token, params=params)

        if not r.ok:
            self._handle_error(r, 'getRepoCollaborators')
            return []

        collaborators = r.json()
        if self._extractPaginationLink(r.headers.get("Link"), rel="next"):
            self._paginatedResults(
                endpoint, access_token=access_token, params=params, result_list=collaborators
            )

        return collaborators

    def getPackages(
        self,
        access_token=None,
        organization=None,
        package_type=None,
        per_page=100,
        visibility=None,
        **kwargs,
    ):
        """Get packages for an organization.

        Args:
            organization: Organization login name
            package_type: 'npm', 'maven', 'rubygems', 'docker', 'nuget', 'container'
                          If None, fetches all types
            visibility: 'public', 'private', 'internal' (optional filter)

        Returns:
            List of package dicts from GitHub API
        """
        if not organization:
            return []

        # If no specific type, fetch all types
        package_types = [package_type] if package_type else [
            'npm', 'maven', 'rubygems', 'docker', 'nuget', 'container'
        ]

        all_packages = []
        for pkg_type in package_types:
            params = {"per_page": per_page, "package_type": pkg_type}
            if visibility:
                params["visibility"] = visibility
            params.update(kwargs)

            endpoint = f"/orgs/{organization}/packages"

            r = self._auth_request(endpoint, access_token, params=params)

            if not r.ok:
                # 404 means no packages of this type, not an error
                # 401/403 are auth errors that should be raised
                if r.status_code in (401, 403):
                    self._handle_error(r, 'getPackages')
                continue

            packages = r.json()
            if self._extractPaginationLink(r.headers.get("Link"), rel="next"):
                self._paginatedResults(
                    endpoint, access_token=access_token, params=params, result_list=packages
                )
            all_packages.extend(packages)

        return all_packages

    def getTags(
        self,
        access_token=None,
        owner=None,
        repo=None,
        per_page=100,
        **kwargs,
    ):
        """Get tags for a repository.

        Args:
            owner: Repository owner (org or user)
            repo: Repository name

        Returns:
            List of tag dicts from GitHub API
        """
        params = {"per_page": per_page, **kwargs}

        if not owner or not repo:
            return []

        endpoint = f"/repos/{owner}/{repo}/tags"

        r = self._auth_request(endpoint, access_token, params=params)

        if not r.ok:
            self._handle_error(r, 'getTags')
            return []

        tags = r.json()
        if self._extractPaginationLink(r.headers.get("Link"), rel="next"):
            self._paginatedResults(
                endpoint, access_token=access_token, params=params, result_list=tags
            )

        return tags

    def getBranches(
        self,
        access_token=None,
        owner=None,
        repo=None,
        per_page=100,
        **kwargs,
    ):
        """Get branches for a repository.

        Args:
            owner: Repository owner (org or user)
            repo: Repository name

        Returns:
            List of branch dicts from GitHub API
        """
        params = {"per_page": per_page, **kwargs}

        if not owner or not repo:
            return []

        endpoint = f"/repos/{owner}/{repo}/branches"

        r = self._auth_request(endpoint, access_token, params=params)

        if not r.ok:
            self._handle_error(r, 'getBranches')
            return []

        branches = r.json()
        if self._extractPaginationLink(r.headers.get("Link"), rel="next"):
            self._paginatedResults(
                endpoint, access_token=access_token, params=params, result_list=branches
            )

        return branches

    def getCommits(
        self,
        access_token=None,
        owner=None,
        repo=None,
        sha=None,
        per_page=100,
        since=None,
        paginate=True,
        **kwargs,
    ):
        """Get commits for a repository branch.

        Args:
            owner: Repository owner (org or user)
            repo: Repository name
            sha: Branch name or commit SHA to start from
            per_page: Number of results per page (max 100)
            since: ISO 8601 timestamp to filter commits after
            paginate: If False, return only the first page of results

        Returns:
            List of commit dicts from GitHub API
        """
        params = {"per_page": per_page, **kwargs}
        if sha:
            params["sha"] = sha
        if since:
            params["since"] = since

        if not owner or not repo:
            return []

        endpoint = f"/repos/{owner}/{repo}/commits"

        r = self._auth_request(endpoint, access_token, params=params)

        if not r.ok:
            self._handle_error(r, 'getCommits')
            return []

        commits = r.json()
        if paginate and self._extractPaginationLink(r.headers.get("Link"), rel="next"):
            self._paginatedResults(
                endpoint, access_token=access_token, params=params, result_list=commits
            )

        return commits

    def getRepositoryTopics(
        self,
        access_token=None,
        owner=None,
        repo=None,
        **kwargs,
    ):
        """Get topics (catalog tags) for a repository.

        Args:
            owner: Repository owner (org or user)
            repo: Repository name

        Returns:
            List of topic names (strings)
        """
        if not owner or not repo:
            return []

        endpoint = f"/repos/{owner}/{repo}/topics"

        r = self._auth_request(endpoint, access_token)

        if not r.ok:
            self._handle_error(r, 'getRepositoryTopics')
            return []

        data = r.json()
        return data.get('names', [])

    def getRepositoryLabels(
        self,
        access_token=None,
        owner=None,
        repo=None,
        per_page=100,
        **kwargs,
    ):
        """Get labels for a repository.

        Args:
            owner: Repository owner (org or user)
            repo: Repository name
            per_page: Number of results per page (max 100)

        Returns:
            List of label dicts with id, name, color, description
        """
        if not owner or not repo:
            return []

        endpoint = f"/repos/{owner}/{repo}/labels"
        params = {"per_page": per_page}

        r = self._auth_request(endpoint, access_token, params=params)

        if not r.ok:
            self._handle_error(r, 'getRepositoryLabels')
            return []

        labels = r.json()
        if self._extractPaginationLink(r.headers.get("Link"), rel="next"):
            self._paginatedResults(
                endpoint,
                access_token=access_token,
                params=params,
                result_list=labels,
            )

        return labels

    def setRepositoryTopics(
        self,
        access_token=None,
        owner=None,
        repo=None,
        topics=None,
        **kwargs,
    ):
        """Set topics (catalog tags) for a repository.

        Args:
            owner: Repository owner (org or user)
            repo: Repository name
            topics: List of topic names (strings)

        Returns:
            True if successful, False otherwise
        """
        if not owner or not repo:
            return False

        if topics is None:
            topics = []

        endpoint = f"/repos/{owner}/{repo}/topics"

        r = self._auth_request(endpoint, access_token, method="put", json={"names": topics})

        if not r.ok:
            self._handle_error(r, 'setRepositoryTopics')
            return False

        return True

    def getPackageVersions(
        self,
        access_token=None,
        organization=None,
        package_type=None,
        package_name=None,
        per_page=100,
        **kwargs,
    ):
        """Get versions for a specific package.

        Args:
            organization: Organization login name
            package_type: Package type (npm, maven, etc.)
            package_name: Package name

        Returns:
            List of version dicts from GitHub API
        """
        if not organization or not package_type or not package_name:
            return []

        params = {"per_page": per_page, **kwargs}
        endpoint = f"/orgs/{organization}/packages/{package_type}/{package_name}/versions"

        r = self._auth_request(endpoint, access_token, params=params)

        if not r.ok:
            self._handle_error(r, 'getPackageVersions')
            return []

        versions = r.json()
        if self._extractPaginationLink(r.headers.get("Link"), rel="next"):
            self._paginatedResults(
                endpoint, access_token=access_token, params=params, result_list=versions
            )

        return versions

    def addCollaborator(
        self,
        access_token=None,
        owner=None,
        repo=None,
        username=None,
        permission='push',
        **kwargs,
    ):
        """Add or update a collaborator's permission on a repository.

        Args:
            owner: Repository owner (org or user)
            repo: Repository name
            username: GitHub username to add/update
            permission: Permission level - 'pull' (read), 'triage', 'push' (write),
                       'maintain', 'admin'

        Returns:
            True if successful, False otherwise
        """
        if not owner or not repo or not username:
            return False

        endpoint = f"/repos/{owner}/{repo}/collaborators/{username}"

        r = self._auth_request(endpoint, access_token, method="put",
                              json={"permission": permission})

        if not r.ok:
            self._handle_error(r, 'addCollaborator')
            return False

        return True

    def getToken(self, code=None, client_id=None, client_secret=None):
        """Returns access token using OAuth flow.

        Args:
            code: OAuth authorization code
            client_id: GitHub OAuth App client ID
            client_secret: GitHub OAuth App client secret

        Returns:
            Tuple of (access_token, refresh_token)
        """
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        data = {"grant_type": "authorization_code", "code": code}

        r = requests.post(
            f"{AUTH_API_URL}/access_token",
            headers=headers,
            data=data,
            auth=(client_id, client_secret),
        )

        if not r.ok:
            self._handle_error(r, 'getToken')
            return None, None

        result = r.json()
        access_token = result.get("access_token")
        refresh_token = result.get("refresh_token")
        return access_token, refresh_token

    def countLinesOfCode(self, username=None, reponame=None):
        "Counts line of code of a Github repository."
        r = requests.get(
            f"https://api.codetabs.com/v1/loc?github={username}/{reponame}",
            timeout=30
        )
        if not r.ok:
            logger.error(
                "**Github** Error (countLinesOfCode) / http code: %s, body message: %s",
                str(r.status_code),
                str(r.content),
            )
            return None

        result = json.loads(r.text)
        return result

    def _paginatedResults(
        self, initial_url, access_token=None, params=None, result_list=None
    ):
        """Handles paginated requests and appends results to the given list."""
        params = params or {}
        result_list = result_list or []

        endpoint = initial_url
        while endpoint:
            r = self._auth_request(endpoint, access_token, params=params)
            if not r.ok:
                self._handle_error(r, '_paginatedResults')
                break

            result_list.extend(r.json())
            endpoint = self._extractPaginationLink(r.headers.get("Link"), rel="next")

        return result_list

    def _extractPaginationLink(self, link_header, rel="next"):
        """Extracts a specific link (e.g., 'next', 'last') from the Link header."""
        if not link_header:
            return None
        links = {}
        # Split by ', <' to handle URLs that may contain commas in query params
        parts = link_header.split(', <')
        for i, part in enumerate(parts):
            # First part starts with '<', others don't after split
            if i == 0:
                part = part[1:]  # Remove leading '<'
            # Split on '>; ' to separate URL from rel
            if '>; ' in part:
                url, rel_part = part.split('>; ', 1)
                # Extract rel value from 'rel="next"'
                if 'rel="' in rel_part:
                    rel_value = rel_part.split('rel="')[1].split('"')[0]
                    links[rel_value] = url
        return links.get(rel)

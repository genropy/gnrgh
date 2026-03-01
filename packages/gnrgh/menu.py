# encoding: utf-8
class Menu(object):
    def config(self, root, **kwargs):
        git = root.branch("!![en]GitHub")
        # Structure
        git.thpage("!![en]Organizations", table="gnrgh.organization")
        git.thpage("!![en]Repositories", table="gnrgh.repository", th_from_package='gnrgh')
        git.thpage("!![en]Branches", table="gnrgh.branch")
        git.thpage("!![en]Commits", table="gnrgh.commit")
        # Collaboration
        git.thpage("!![en]Issues", table="gnrgh.issue")
        git.thpage("!![en]Pull Requests", table="gnrgh.pull_request")
        # Users & Artifacts
        git.thpage("!![en]GitHub Users", table="gnrgh.gh_user")
        git.thpage("!![en]Artifacts", table="gnrgh.gh_artifact")
        # Tools
        git.webpage("!![en]IDE", filepath="/gnrgh/gnride")
        # Admin
        git.thpage("!![en]Webhook Events", table="gnrgh.webhook_event")
        git.lookupBranch("!![en]Utility tables", pkg="gnrgh")

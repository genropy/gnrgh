# encoding: utf-8
import json
from gnr.core.gnrbag import Bag

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('webhook_event', pkey='id', name_long='!![en]Webhook Event',
                        name_plural='!![en]Webhook Events', caption_field='delivery_id')
        self.sysFields(tbl)

        # GitHub delivery identity
        tbl.column('delivery_id', unique=True, indexed=True, name_long='!![en]Delivery ID')  # X-GitHub-Delivery header

        # Event info
        tbl.column('event', indexed=True, name_long='!![en]Event')  # "issues", "push", "pull_request", etc.
        tbl.column('action', indexed=True, name_long='!![en]Action')  # "opened", "closed", "edited", etc.

        # The server that sent the event: known from the webhook url before
        # the payload is read
        tbl.column('git_host_id', size='22', group='_', name_long='!![en]Git Host').relation(
            'git_host.id', relation_name='webhook_events', mode='foreignkey', onDelete='raise')

        # Relation to repository (nullable - some events may not have a repo)
        tbl.column('repo_id', size='22', name_long='!![en]Repository').relation(
            'repository.id', relation_name='webhook_events', mode='foreignkey', onDelete='setnull')

        # Relation to organization (nullable - some events may not have an org)
        tbl.column('organization_id', size='22', name_long='!![en]Organization').relation(
            'organization.id', relation_name='webhook_events', mode='foreignkey', onDelete='setnull')

        # Alias columns
        tbl.aliasColumn('repo_group', '@repo_id.repo_group',
                        name_long='!![en]Group')

        # Timestamps
        tbl.column('received_at', dtype='DHZ', indexed=True, name_long='!![en]Received At')

        # Raw payload
        tbl.column('payload', dtype='X', name_long='!![en]Payload')

        # The row the event was about, resolved within git_host_id when the
        # event is processed
        tbl.column('issue_id', size='22', group='_', name_long='!![en]Issue').relation(
            'issue.id', relation_name='webhook_events', mode='foreignkey', onDelete='setnull')
        tbl.column('pull_request_id', size='22', group='_', name_long='!![en]Pull request').relation(
            'pull_request.id', relation_name='webhook_events', mode='foreignkey', onDelete='setnull')

    def trigger_onInserted(self, record):
        """Process webhook payload when a new event is inserted"""
        self.processWebhookPayload(record)

    def storeEvent(self, payload, git_host_id=None, event=None, delivery_id=None, received_at=None):
        """Save a received webhook event (processed by trigger_onInserted).

        A Forgejo system webhook sends the events of every repository of the
        instance: events of an organization unknown to gnrgh (personal
        repositories, organizations not imported) are not stored.

        Args:
            git_host_id: the server that sent the event, from the webhook url

        Returns:
            The pkey of the stored event, or None if ignored
        """
        forge_type = self.db.table('gnrgh.git_host').readColumns(pkey=git_host_id, columns='$type')
        if not forge_type:
            raise ValueError(f'Unknown git_host {git_host_id}')
        repo_id, organization_id = self.resolveEventSource(payload, git_host_id=git_host_id,
                                                           is_forgejo=forge_type == 'forgejo')
        if forge_type == 'forgejo' and not organization_id:
            return None
        record = self.newrecord(delivery_id=delivery_id, event=event, action=payload.get('action'),
                                git_host_id=git_host_id, repo_id=repo_id,
                                organization_id=organization_id,
                                received_at=received_at, payload=payload)
        self.insert(record)
        return record['id']

    def resolveEventSource(self, payload, git_host_id=None, is_forgejo=False):
        """Find repository and organization of a webhook payload within its server.

        GitHub payloads carry `organization`; Forgejo payloads carry it only in
        repository events, otherwise the organization is the repository owner.

        Returns:
            (repository_id, organization_id), each None when not found
        """
        repo_data = payload.get('repository') or {}
        org_login = (payload.get('organization') or {}).get('login')
        if not org_login and is_forgejo:
            org_login = (repo_data.get('owner') or {}).get('login')
        organization_id = None
        if org_login:
            org_record = self.db.table('gnrgh.organization').query(
                where='$login=:login AND $git_host_id=:gh', login=org_login, gh=git_host_id,
                columns='$id'
            ).fetch()
            if org_record:
                organization_id = org_record[0]['id']
        repo_id = None
        if repo_data.get('full_name'):
            repo_record = self.db.table('gnrgh.repository').query(
                where='$full_name=:fn AND $git_host_id=:gh',
                fn=repo_data['full_name'], gh=git_host_id, columns='$id'
            ).fetch()
            if repo_record:
                repo_id = repo_record[0]['id']
        return repo_id, organization_id

    def processWebhookPayload(self, record):
        """Process webhook payload and delegate to the appropriate table's processEvent method"""
        try:
            # Parse payload
            payload_str = record['payload']
            if isinstance(payload_str, str):
                payload = json.loads(payload_str)
            elif isinstance(payload_str, Bag):
                payload = dict(payload_str)
            else:
                payload = payload_str

            event_type = record['event']
            # create/delete payloads have no action: branch.processEvent expects the event name
            action = record['action'] or (event_type if event_type in ('create', 'delete') else None)

            # Events of an inactive organization are kept but not processed
            organization_id = record['organization_id']
            if organization_id and self.db.table('gnrgh.organization').readColumns(
                    pkey=organization_id, columns='$inactive'):
                return

            # Forgejo payloads have no `organization` outside repository events:
            # give the tables the organization resolved by receiveWebhook
            if organization_id and not payload.get('organization'):
                org_github_id, org_login = self.db.table('gnrgh.organization').readColumns(
                    pkey=organization_id, columns='$github_id,$login')
                payload['organization'] = {'id': org_github_id, 'login': org_login}

            # Map event types to their corresponding tables
            event_table_map = {
                'issues': 'gnrgh.issue',
                'issue_comment': 'gnrgh.issue_comment',
                'pull_request': 'gnrgh.pull_request',
                'repository': 'gnrgh.repository',
                'organization': 'gnrgh.organization',
                'push': 'gnrgh.repository',  # push events update repository metadata
                'create': 'gnrgh.branch',  # branch/tag creation
                'delete': 'gnrgh.branch',  # branch/tag deletion
            }

            # Get the appropriate table and delegate to its processEvent method
            table_name = event_table_map.get(event_type)
            if table_name:
                target_table = self.db.table(table_name)
                target_pkey = target_table.processEvent(payload, action=action,
                                                        git_host_id=record['git_host_id'])
                # link the event to the row it was about
                if target_pkey and table_name in ('gnrgh.issue', 'gnrgh.pull_request'):
                    link_field = 'issue_id' if table_name == 'gnrgh.issue' else 'pull_request_id'
                    self.batchUpdate({link_field: target_pkey}, pkey=record['id'])

        except Exception as e:
            # Log error but don't fail the insert
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error processing webhook payload for delivery {record['delivery_id']}: {str(e)}")

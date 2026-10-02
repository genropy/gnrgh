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

        # bag items columns to filter out based on the derived model starting
        # from the event generating the record
        tbl.bagItemColumn('issue', bagcolumn='$payload',
                          dtype='L',
                          itempath='issue.id',
                          name_long='!![en]Issue').relation(
                              'issue.github_id', relation_name="source_events"
                         )
        tbl.bagItemColumn('pull_request', bagcolumn='$payload',
                          dtype='L',
                          itempath='pull_request.id',
                          name_long='!![en]Pull request').relation(
                              'pull_request.github_id', relation_name="source_events"
                         )
        tbl.bagItemColumn('repository', bagcolumn='$payload',
                          dtype='L',
                          itempath='repository.id',
                          name_long='!![en]Repository').relation(
                              'repository.github_id', relation_name="source_events"
                         )
        tbl.bagItemColumn('organization', bagcolumn='$payload',
                          dtype='L',
                          itempath='organization.id',
                          name_long='!![en]Organization').relation(
                              'organization.github_id', relation_name="source_events"
                         )


    def trigger_onInserted(self, record):
        """Process webhook payload when a new event is inserted"""
        self.processWebhookPayload(record)

    def resolveEventSource(self, payload, is_forgejo=False):
        """Find repository and organization of a webhook payload within its forge.

        GitHub payloads carry `organization`; Forgejo payloads carry it only in
        repository events, otherwise the organization is the repository owner.

        Returns:
            (repository_id, organization_id), each None when not found
        """
        forge_where = '$api_url IS NOT NULL' if is_forgejo else '$api_url IS NULL'
        repo_data = payload.get('repository') or {}
        org_login = (payload.get('organization') or {}).get('login')
        if not org_login and is_forgejo:
            org_login = (repo_data.get('owner') or {}).get('login')
        organization_id = None
        if org_login:
            org_record = self.db.table('gnrgh.organization').query(
                where=f'$login=:login AND {forge_where}', login=org_login, columns='$id'
            ).fetch()
            if org_record:
                organization_id = org_record[0]['id']
        repo_id = None
        if repo_data.get('full_name'):
            repo_record = self.db.table('gnrgh.repository').query(
                where=f'$full_name=:fn AND @organization_id.{forge_where[1:]}',
                fn=repo_data['full_name'], columns='$id'
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
            action = record['action']

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
                target_table.processEvent(payload, action=action)

        except Exception as e:
            # Log error but don't fail the insert
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error processing webhook payload for delivery {record['delivery_id']}: {str(e)}")

# -*- coding: utf-8 -*-

import base64
import json
import hmac
import hashlib
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import GnrException
from datetime import datetime

class GnrCustomWebPage(object):
    py_requires = 'gnrcomponents/externalcall:BaseRpc'

    @public_method
    def receiveWebhook(self, **kwargs):
        """
        Receives and processes GitHub webhooks.
        Authenticates the request using the webhook_secret preference
        and saves the event to the webhook_event table.
        """
        # Get the webhook secret from package preferences
        webhook_secret = self.db.application.getPreference('webhook_secret', pkg='gnrgh')

        if not webhook_secret:
            raise GnrException('!![en]GitHub webhook secret is not configured')

        # Get GitHub webhook headers
        github_signature = self.request.get_header('X-Hub-Signature-256')
        delivery_id = self.request.get_header('X-GitHub-Delivery')
        event_type = self.request.get_header('X-GitHub-Event')

        if not github_signature:
            raise GnrException('!![en]Missing X-Hub-Signature-256 header')

        # Get the raw request body from Werkzeug cache
        # (get_json in parse_request_params already called get_data(cache=True))
        raw_body = self.request.get_data(cache=True)

        # Ensure raw_body is bytes
        if isinstance(raw_body, str):
            raw_body = raw_body.encode('utf-8')

        # Verify the signature
        expected_signature = 'sha256=' + hmac.new(
            webhook_secret.encode('utf-8'),
            raw_body,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(github_signature, expected_signature):
            import logging
            logging.getLogger('gnr.webhook').error(
                'HMAC mismatch: body_len=%s body_preview=%r has_json_body=%s',
                len(raw_body), raw_body[:100], '_json_body' in kwargs
            )
            raise GnrException('!![en]Invalid webhook signature')

        # Parse the payload
        try:
            if isinstance(raw_body, bytes):
                payload_data = json.loads(raw_body.decode('utf-8'))
            else:
                payload_data = json.loads(raw_body)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise GnrException(f'!![en]Failed to parse webhook payload: {str(e)}')

        # Extract action if present
        action = payload_data.get('action')

        # Extract repository ID if present
        repo_id = None
        if 'repository' in payload_data:
            repo_full_name = payload_data['repository'].get('full_name')
            if repo_full_name:
                # Try to find the repository in our database
                repo_record = self.db.table('gnrgh.repository').query(
                    where='$full_name=:fn', fn=repo_full_name
                ).fetch()
                if repo_record:
                    repo_id = repo_record[0]['id']

        # Extract organization ID if present
        organization_id = None
        if 'organization' in payload_data:
            org_login = payload_data['organization'].get('login')
            if org_login:
                # Try to find the organization in our database
                org_record = self.db.table('gnrgh.organization').query(
                    where='$login=:login', login=org_login
                ).fetch()
                if org_record:
                    organization_id = org_record[0]['id']

        # Save the webhook event
        webhook_tbl = self.db.table('gnrgh.webhook_event')
        record = webhook_tbl.newrecord(
            delivery_id=delivery_id,
            event=event_type,
            action=action,
            repo_id=repo_id,
            organization_id=organization_id,
            received_at=datetime.now(),
            payload=payload_data
        )
        webhook_tbl.insert(record)
        self.db.commit()

        return {'success': True, 'delivery_id': delivery_id, 'event': event_type}

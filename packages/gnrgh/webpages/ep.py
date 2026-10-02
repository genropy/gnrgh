# -*- coding: utf-8 -*-

import json
import hmac
import hashlib
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrlang import GnrException
from datetime import datetime, timezone

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
            raise GnrException('!![en]Invalid webhook signature')

        try:
            if isinstance(raw_body, bytes):
                payload_data = json.loads(raw_body.decode('utf-8')) 
            else:
                payload_data = json.loads(raw_body)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise GnrException(f'!![en]Failed to parse webhook payload: {str(e)}')           

        # Forgejo sends the GitHub headers too, plus its own X-Forgejo-*
        is_forgejo = bool(self.request.get_header('X-Forgejo-Event'))
        stored = self.db.table('gnrgh.webhook_event').storeEvent(
            payload_data, event=event_type, delivery_id=delivery_id,
            received_at=datetime.now(timezone.utc), is_forgejo=is_forgejo)
        self.db.commit()

        return {'success': True, 'delivery_id': delivery_id, 'event': event_type, 'ignored': not stored}

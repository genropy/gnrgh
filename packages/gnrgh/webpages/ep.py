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
    def receiveWebhook(self, git_host_id=None, **kwargs):
        """
        Receives and processes GitHub and Forgejo webhooks.
        Authenticates the request using the webhook_secret preference
        and saves the event to the webhook_event table.

        The url of the webhook names the server: /ep/receiveWebhook/<git_host_id>.
        Without git_host_id (webhooks configured before git_host existed) the
        event is attributed to github.com; a Forgejo event without git_host_id
        is rejected. The signature is checked with the secret of that host.
        """
        git_host_tbl = self.db.table('gnrgh.git_host')
        if not git_host_id:
            # Forgejo sends the GitHub headers too, plus its own X-Forgejo-*
            if self.request.get_header('X-Forgejo-Event'):
                raise GnrException('!![en]Forgejo webhooks need the git_host_id in their url')
            git_host_id = git_host_tbl.githubHost()
        webhook_secret = git_host_tbl.readColumns(pkey=git_host_id, columns='$webhook_secret')
        if not webhook_secret:
            raise GnrException('!![en]Webhook secret is not configured for this git host')

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

        stored = self.db.table('gnrgh.webhook_event').storeEvent(
            payload_data, git_host_id=git_host_id, event=event_type, delivery_id=delivery_id,
            received_at=datetime.now(timezone.utc))
        self.db.commit()

        return {'success': True, 'delivery_id': delivery_id, 'event': event_type, 'ignored': not stored}

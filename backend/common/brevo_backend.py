"""
Django email backend that sends via Brevo's HTTP API instead of raw SMTP.

Why it exists: Render blocks outbound SMTP connections — the welcome email's
smtplib connect to smtp-relay.brevo.com:587 hung ~133s and died with
TimeoutError [Errno 110] (packets silently dropped). HTTPS (443) is always
allowed, so transactional email goes out as an API call to
https://api.brevo.com/v3/smtp/email.

Activation: set BREVO_API_KEY in the environment — core/settings/production.py
switches EMAIL_BACKEND to this backend automatically when the key is present.
Without the key, the configured (SMTP) backend is kept and behaviour is
unchanged. The API key is generated in Brevo → SMTP & API → API Keys; it is
a different credential from the SMTP key.
"""

import json
import logging

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

# Well under any request-path budget; the Celery/thread dispatch context
# tolerates more, but a fast, loud failure beats a silent 2-minute hang.
BREVO_API_TIMEOUT = 15  # seconds


def _parse_address(value: str) -> dict:
    """
    Convert a Django-style address into Brevo's {"name": ..., "email": ...}.

    'Name <a@b.c>' → {"name": "Name", "email": "a@b.c"}
    'a@b.c'        → {"email": "a@b.c"}
    """
    value = (value or "").strip()
    if "<" in value and value.endswith(">"):
        name, _, email = value[:-1].partition("<")
        return {"name": name.strip() or email.strip(), "email": email.strip()}
    return {"email": value}


class BrevoApiBackend(BaseEmailBackend):
    """
    Django email backend sending via the Brevo v3 /smtp/email endpoint.

    Supports plain-text bodies and HTML alternatives. Failures raise (unless
    fail_silently) so callers like NotificationService log the real Brevo
    error response instead of an opaque network timeout.
    """

    def send_messages(self, email_messages) -> int:
        if not email_messages:
            return 0

        api_key = getattr(settings, "BREVO_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "BrevoApiBackend selected but BREVO_API_KEY is not configured."
            )

        session = requests.Session()
        session.headers.update({
            "api-key": api_key,
            "content-type": "application/json",
            "accept": "application/json",
        })

        sent = 0
        for message in email_messages:
            try:
                self._send_one(session, message)
                sent += 1
            except Exception:
                if not self.fail_silently:
                    raise
                logger.error(
                    "BrevoApiBackend: failed to send message to %s",
                    message.to,
                    exc_info=True,
                )
        return sent

    def _send_one(self, session: requests.Session, message) -> None:
        html = None
        text = (message.body or "").strip() or None
        for content, mimetype in getattr(message, "alternatives", None) or []:
            if mimetype == "text/html":
                html = content

        payload: dict = {
            "sender": _parse_address(
                message.from_email or settings.DEFAULT_FROM_EMAIL
            ),
            "to": [_parse_address(addr) for addr in message.to],
            "subject": message.subject or "",
        }
        if text:
            payload["textContent"] = text
        if html:
            payload["htmlContent"] = html
        if message.cc:
            payload["cc"] = [_parse_address(addr) for addr in message.cc]
        if message.bcc:
            payload["bcc"] = [_parse_address(addr) for addr in message.bcc]
        if message.reply_to:
            payload["replyTo"] = [_parse_address(addr) for addr in message.reply_to]

        response = session.post(
            BREVO_API_URL, data=json.dumps(payload), timeout=BREVO_API_TIMEOUT
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"Brevo API error {response.status_code}: {response.text[:300]}"
            )

        logger.info(
            "BrevoApiBackend: sent message to %s (messageId=%s)",
            message.to,
            response.json().get("messageId", "?"),
        )

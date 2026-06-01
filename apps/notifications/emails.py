"""
Notification email builders.

Each function returns a fully constructed EmailMessage object ready to send.
No sending logic lives here — that belongs in notifications/tasks.py.

Responsibilities:
- Build email subject, plain-text body, and HTML body
- Return a ready-to-send EmailMessage object

Rule 14 (one responsibility per function):
- Each builder builds exactly one email type
- Sending is handled by notifications/tasks.py → NotificationService

Rule 9 (no hidden side effects):
- No DB writes
- No event firing
- Pure construction functions
"""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


def build_welcome_email(user_email: str, display_name: str = "") -> EmailMultiAlternatives:
    """
    Build the welcome email sent to a user immediately after registration.

    Returns a fully constructed EmailMultiAlternatives (supports both
    plain-text and HTML). The caller is responsible for calling .send().

    Args:
        user_email:    Recipient email address.
        display_name:  User's display name, if set. Falls back to "there"
                       for a generic greeting if empty.
    """
    name = display_name.strip() if display_name.strip() else "there"
    subject = "Welcome to STEM Platform 🎓"
    from_email = settings.DEFAULT_FROM_EMAIL
    to = [user_email]

    # ── Plain-text body ───────────────────────────────────────────────────────
    text_body = f"""Hi {name},

Welcome to STEM Platform — your home for structured STEM learning.

Here's what you can do right now:
  • Browse courses across Computer Science, Mathematics, Sciences, and more
  • Follow a guided Combo (learning path) to build skills step by step
  • Track your progress and save courses to come back to later

Get started: {settings.FRONTEND_URL}/courses

If you have any questions, just reply to this email.

Happy learning,
The STEM Platform Team
"""

    # ── HTML body ─────────────────────────────────────────────────────────────
    # Inline styles only — no external CSS. Safe across all email clients.
    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Welcome to STEM Platform</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f6f9;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f6f9;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0"
               style="background-color:#ffffff;border-radius:8px;overflow:hidden;
                      box-shadow:0 2px 8px rgba(0,0,0,0.08);">

          <!-- Header -->
          <tr>
            <td style="background-color:#1a56db;padding:32px 40px;text-align:center;">
              <h1 style="color:#ffffff;margin:0;font-size:24px;font-weight:700;
                         letter-spacing:-0.5px;">
                STEM Platform
              </h1>
              <p style="color:#bfdbfe;margin:8px 0 0 0;font-size:14px;">
                Structured learning for every stage
              </p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:40px 40px 32px 40px;">
              <h2 style="color:#111827;font-size:20px;margin:0 0 16px 0;">
                Hi {name} 👋
              </h2>
              <p style="color:#374151;font-size:15px;line-height:1.7;margin:0 0 24px 0;">
                Welcome to STEM Platform — your home for structured, guided STEM learning.
                Whether you're just starting out or deepening your expertise, we've built
                the tools to keep you on track.
              </p>

              <!-- Feature list -->
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="background-color:#f9fafb;border-radius:6px;
                            padding:0;margin-bottom:28px;">
                <tr>
                  <td style="padding:20px 24px;">
                    <p style="color:#111827;font-size:14px;font-weight:700;
                               margin:0 0 12px 0;text-transform:uppercase;
                               letter-spacing:0.5px;">
                      What you can do right now
                    </p>
                    <p style="color:#374151;font-size:14px;line-height:1.8;margin:0;">
                      📚 &nbsp;Browse courses across CS, Mathematics, Sciences, and more<br>
                      🛤️ &nbsp;Follow a guided <strong>Combo</strong> to build skills step by step<br>
                      ✅ &nbsp;Track your progress and save content to revisit later
                    </p>
                  </td>
                </tr>
              </table>

              <!-- CTA button -->
              <table cellpadding="0" cellspacing="0" style="margin:0 auto 32px auto;">
                <tr>
                  <td style="background-color:#1a56db;border-radius:6px;text-align:center;">
                    <a href="{settings.FRONTEND_URL}/courses"
                       style="display:inline-block;padding:14px 32px;color:#ffffff;
                              font-size:15px;font-weight:600;text-decoration:none;">
                      Start Exploring →
                    </a>
                  </td>
                </tr>
              </table>

              <p style="color:#6b7280;font-size:14px;line-height:1.7;margin:0;">
                If you have any questions, just reply to this email — we read every message.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color:#f9fafb;padding:24px 40px;
                       border-top:1px solid #e5e7eb;text-align:center;">
              <p style="color:#9ca3af;font-size:12px;margin:0;line-height:1.6;">
                You received this email because you signed up at STEM Platform.<br>
                © 2025 STEM Platform. All rights reserved.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email,
        to=to,
    )
    message.attach_alternative(html_body, "text/html")

    logger.debug(
        "build_welcome_email: Email constructed for %s",
        user_email,
    )
    return message
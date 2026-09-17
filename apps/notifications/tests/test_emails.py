"""
Tests for notifications/emails.py.

emails.py contains pure construction functions (Rule 9: no DB writes, no
event firing, no sending). These tests check the EmailMultiAlternatives
object is built correctly — not that it was actually delivered.
"""

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from apps.notifications.emails import build_welcome_email


class TestBuildWelcomeEmail:
    def test_returns_email_multi_alternatives(self):
        email = build_welcome_email(user_email="jane@example.com", display_name="Jane")
        assert isinstance(email, EmailMultiAlternatives)

    def test_sets_recipient(self):
        email = build_welcome_email(user_email="jane@example.com", display_name="Jane")
        assert email.to == ["jane@example.com"]

    def test_sets_from_email_from_settings(self):
        email = build_welcome_email(user_email="jane@example.com", display_name="Jane")
        assert email.from_email == settings.DEFAULT_FROM_EMAIL

    def test_subject_is_set(self):
        email = build_welcome_email(user_email="jane@example.com", display_name="Jane")
        assert email.subject == "Welcome to STEM Platform 🎓"

    def test_greets_user_by_display_name(self):
        email = build_welcome_email(user_email="jane@example.com", display_name="Jane")
        assert "Hi Jane" in email.body

    def test_falls_back_to_generic_greeting_when_display_name_blank(self):
        email = build_welcome_email(user_email="jane@example.com", display_name="")
        assert "Hi there" in email.body

    def test_falls_back_to_generic_greeting_when_display_name_whitespace_only(self):
        email = build_welcome_email(user_email="jane@example.com", display_name="   ")
        assert "Hi there" in email.body

    def test_body_links_to_frontend_courses_page(self):
        email = build_welcome_email(user_email="jane@example.com", display_name="Jane")
        assert f"{settings.FRONTEND_URL}/courses" in email.body

    def test_attaches_html_alternative(self):
        email = build_welcome_email(user_email="jane@example.com", display_name="Jane")
        assert len(email.alternatives) == 1
        html_body, mimetype = email.alternatives[0]
        assert mimetype == "text/html"
        assert "<html" in html_body
        assert f"{settings.FRONTEND_URL}/courses" in html_body

from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from recipes.models import User


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="noreply@test.com",
)
class PasswordAndUsernameResetViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="johndoe",
            email="test@example.com",
            password="Password123",
        )

    # -----------------------
    # Password reset request
    # -----------------------
    def test_password_reset_get_renders(self):
        url = reverse("password_reset")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

    def test_password_reset_post_unknown_email_does_not_send_mail_but_redirects(self):
        url = reverse("password_reset")
        res = self.client.post(url, data={"email": "unknown@example.com"})
        self.assertEqual(res.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_post_known_email_sends_mail_and_redirects(self):
        url = reverse("password_reset")

        with patch(
            "recipes.views.password_reset_views.PasswordResetRequestView.reset_link_generator",
            return_value="https://example.com/reset-link",
        ):
            res = self.client.post(url, data={"email": self.user.email})

        self.assertEqual(res.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Password Reset Request", mail.outbox[0].subject)
        self.assertIn("https://example.com/reset-link", mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, [self.user.email])

    def test_password_reset_post_known_email_no_link_does_not_send_mail(self):
        url = reverse("password_reset")

        with patch(
            "recipes.views.password_reset_views.PasswordResetRequestView.reset_link_generator",
            return_value=None,
        ):
            res = self.client.post(url, data={"email": self.user.email})

        self.assertEqual(res.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_redirects_when_logged_in(self):
        self.client.force_login(self.user)
        url = reverse("password_reset")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 302)  # LoginProhibitedMixin should redirect

    # -----------------------
    # Username reset request
    # -----------------------
    def test_username_reset_get_renders(self):
        url = reverse("username_reset")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

    def test_username_reset_post_unknown_email_does_not_send_mail_but_redirects(self):
        url = reverse("username_reset")
        res = self.client.post(url, data={"email": "unknown@example.com"})
        self.assertEqual(res.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)

    def test_username_reset_post_known_email_sends_mail_and_redirects(self):
        url = reverse("username_reset")
        res = self.client.post(url, data={"email": self.user.email})

        self.assertEqual(res.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Username Recovery", mail.outbox[0].subject)
        self.assertIn(self.user.username, mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, [self.user.email])

    def test_username_reset_redirects_when_logged_in(self):
        self.client.force_login(self.user)
        url = reverse("username_reset")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 302)
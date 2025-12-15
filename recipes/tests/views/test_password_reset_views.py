from django.test import TestCase
from django.urls import reverse
from recipes.models import User
from django.core import mail

class PasswordResetViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='johndoe',
            email='test@example.com',
            password='Password123'
        )
        self.url = reverse('password_reset')

    def test_get_request_renders_template(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth/password_reset_request.html')

    def test_post_valid_email_sends_mail(self):
        response = self.client.post(self.url, {'email': 'test@example.com'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.url, response.url)

    def test_post_unknown_email_redirects_safely(self):
        response = self.client.post(self.url, {'email': 'unknown@example.com'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)

class UsernameResetViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='johndoe',
            email='test@example.com',
            password='Password123'
        )
        self.url = reverse('username_reset')

    def test_simple_template_views(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth/username_reset_request.html')

    def test_post_valid_email_sends_username(self):
        response = self.client.post(self.url, {'email': 'test@example.com'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('johndoe', mail.outbox[0].body)
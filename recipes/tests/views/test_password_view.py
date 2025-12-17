from django.test import TestCase
from django.urls import reverse
from recipes.models import User
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
from recipes.tests.helpers import reverse_with_next

class PasswordViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            'johndoe',
            first_name='John',
            last_name='Doe',
            email='johndoe@example.org',
            password='Password123',
            bio='Bio'
        )
        self.url = reverse('password')
        self.form_input = {
            'password': 'Password123',
            'new_password': 'NewPassword123',
            'password_confirmation': 'NewPassword123'
        }
        
        site = Site.objects.get_current()
        provider = SocialApp.objects.create(
            provider='google',
            name='Google',
            client_id='fake-client-id',
            secret='fake-secret',
        )
        provider.sites.add(site)

    def test_password_url(self):
        self.assertEqual(self.url, '/password/')

    def test_get_password(self):
        self.client.login(email=self.user.email, password='Password123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        # Matches your view's template_name
        self.assertTemplateUsed(response, 'content/password.html')

    def test_get_password_redirects_when_not_logged_in(self):
        response = self.client.get(self.url)
        redirect_url = reverse_with_next('log_in', self.url)
        self.assertRedirects(response, redirect_url, status_code=302, target_status_code=200)

    def test_succesful_password_change(self):
        self.client.login(email=self.user.email, password='Password123')
        response = self.client.post(self.url, self.form_input, follow=True)
        response_url = reverse('dashboard')
        self.assertRedirects(response, response_url, status_code=302, target_status_code=200)
        self.assertTemplateUsed(response, 'app/dashboard.html')
        
        # Verify the password actually changed
        self.user.refresh_from_db()
        is_password_correct = self.user.check_password('NewPassword123')
        self.assertTrue(is_password_correct)

    def test_unsuccesful_password_change(self):
        self.client.login(email=self.user.email, password='Password123')
        self.form_input['new_password'] = 'WrongPassword'
        response = self.client.post(self.url, self.form_input)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'content/password.html')
        form = response.context['form']
        self.assertTrue(form.is_bound)
        
        # Verify password did NOT change
        self.user.refresh_from_db()
        is_password_correct = self.user.check_password('Password123')
        self.assertTrue(is_password_correct)

    def test_post_password_redirects_when_not_logged_in(self):
        response = self.client.post(self.url, self.form_input)
        redirect_url = reverse_with_next('log_in', self.url)
        self.assertRedirects(response, redirect_url, status_code=302, target_status_code=200)
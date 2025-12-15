from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from recipes.forms import LogInForm
from recipes.models import User
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
from recipes.tests.helpers import LogInTester, reverse_with_next

class LogInViewTestCase(TestCase, LogInTester):
    def setUp(self):
        self.url = reverse('log_in')

        site, _ = Site.objects.get_or_create(
            id=settings.SITE_ID,
            defaults={"domain": "example.com", "name": "example.com"},
        )

        provider = SocialApp.objects.create(
            provider='google',
            name='Google',
            client_id='fake-client-id',
            secret='fake-secret',
        )
        provider.sites.add(site)

        self.user = User.objects.create_user(
            'johndoe',
            first_name='John',
            last_name='Doe',
            email='johndoe@example.org',
            password='Password123',
            bio='Bio'
        )

    def test_log_in_url(self):
        self.assertEqual(self.url, '/log_in/')

    def test_get_log_in(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth/log_in.html')
        form = response.context['form']
        self.assertTrue(isinstance(form, LogInForm))
        self.assertFalse(form.is_bound)

    def test_get_log_in_redirects_when_logged_in(self):
        self.client.login(email=self.user.email, password='Password123')
        response = self.client.get(self.url, follow=True)
        redirect_url = reverse('dashboard')
        self.assertRedirects(response, redirect_url, status_code=302, target_status_code=200)
        self.assertTemplateUsed(response, 'app/dashboard.html')

    def test_post_log_in_redirects_when_logged_in(self):
        self.client.login(email=self.user.email, password='Password123')
        form_input = {'email': 'johndoe@example.org', 'password': 'Password123'}
        response = self.client.post(self.url, form_input, follow=True)
        redirect_url = reverse('dashboard')
        self.assertRedirects(response, redirect_url, status_code=302, target_status_code=200)
        self.assertTemplateUsed(response, 'app/dashboard.html')

    def test_unsuccesful_log_in(self):
        form_input = {'email': 'johndoe@example.org', 'password': 'WrongPassword123'}
        response = self.client.post(self.url, form_input)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth/log_in.html')
        form = response.context['form']
        self.assertTrue(isinstance(form, LogInForm))
        self.assertFalse(form.is_valid())
        self.assertFalse(self._is_logged_in())

    def test_succesful_log_in(self):
        form_input = {'username': 'johndoe', 'email': 'johndoe@example.org', 'password': 'Password123'}
        response = self.client.post(self.url, form_input, follow=True)
        response_url = reverse('dashboard')
        self.assertRedirects(response, response_url, status_code=302, target_status_code=200)
        self.assertTemplateUsed(response, 'app/dashboard.html')

    def test_post_log_in_with_incorrect_credentials_and_redirect(self):
        redirect_url = reverse('dashboard')
        url = reverse_with_next('log_in', redirect_url)
        form_input = {'email': 'johndoe@example.org', 'password': 'WrongPassword123'}
        response = self.client.post(url, form_input)
        next_url = response.context['next']
        self.assertEqual(next_url, redirect_url)

    def test_valid_log_in_by_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        form_input = {'email': 'johndoe@example.org', 'password': 'Password123'}
        response = self.client.post(self.url, form_input, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth/log_in.html')
        form = response.context['form']
        self.assertTrue(isinstance(form, LogInForm))
        self.assertFalse(form.is_valid())
        self.assertFalse(self._is_logged_in())

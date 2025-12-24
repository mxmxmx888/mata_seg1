from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from recipes.forms import LogInForm
from recipes.models import User
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
from recipes.tests.test_utils import LogInTester, reverse_with_next

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
        redirect_url = reverse('home')
        self.assertRedirects(response, redirect_url, status_code=302, target_status_code=200)
        self.assertTemplateUsed(response, 'public/home.html')
        self.assertFalse(self._is_logged_in())

    def test_post_log_in_redirects_when_logged_in(self):
        self.client.login(email=self.user.email, password='Password123')
        form_input = {'email': 'johndoe@example.org', 'password': 'Password123'}
        response = self.client.post(self.url, form_input, follow=True)
        redirect_url = reverse('home')
        self.assertRedirects(response, redirect_url, status_code=302, target_status_code=200)
        self.assertTemplateUsed(response, 'public/home.html')
        self.assertFalse(self._is_logged_in())

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

    def test_valid_form_with_no_user_adds_error_and_renders(self):
        with patch("recipes.views.log_in_view.LogInForm") as form_cls:
            form_instance = MagicMock()
            form_instance.is_valid.return_value = True
            form_instance.get_user.return_value = None
            form_cls.return_value = form_instance

            response = self.client.post(self.url, {"username": "johndoe", "password": "Password123"})

            self.assertEqual(response.status_code, 200)
            form_instance.add_error.assert_called_once()
            self.assertTemplateUsed(response, "auth/log_in.html")

    def test_next_parameter_string_none_falls_back_to_dashboard(self):
        form_input = {'username': 'johndoe', 'email': 'johndoe@example.org', 'password': 'Password123'}
        response = self.client.post(self.url + "?next=None", form_input, follow=True)
        self.assertRedirects(response, reverse('dashboard'), status_code=302, target_status_code=200)

    def test_successful_login_respects_next_parameter(self):
        form_input = {'username': 'johndoe', 'email': 'johndoe@example.org', 'password': 'Password123'}
        response = self.client.post(self.url + "?next=/profile/", form_input)
        self.assertRedirects(response, "/profile/", status_code=302, target_status_code=200)

from django.conf import settings
from django.contrib.sites.models import Site
from django.test import TestCase
from django.urls import reverse
from allauth.socialaccount.models import SocialApp

from recipes.forms import SignUpForm
from recipes.models import User
from recipes.tests.test_utils import LogInTester


class SignUpViewTestCase(TestCase, LogInTester):
    def setUp(self):
        self.url = reverse("sign_up")

        site, _ = Site.objects.get_or_create(
            id=settings.SITE_ID,
            defaults={"domain": "example.com", "name": "example.com"},
        )

        provider = SocialApp.objects.create(
            provider="google",
            name="Google",
            client_id="fake-client-id",
            secret="fake-secret",
        )
        provider.sites.add(site)

        self.form_input = {
            "first_name": "Jane",
            "last_name": "Doe",
            "username": "janedoe",
            "email": "janedoe@example.org",
            "new_password": "Password123",
            "password_confirmation": "Password123",
        }
        self.user = User.objects.create_user(
            "@johndoe",
            first_name="John",
            last_name="Doe",
            email="johndoe@example.org",
            password="Password123",
            bio="Bio",
        )

    def test_sign_up_url(self):
        self.assertEqual(self.url, "/sign_up/")

    def test_get_sign_up(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "auth/sign_up.html")
        form = response.context["form"]
        self.assertTrue(isinstance(form, SignUpForm))
        self.assertFalse(form.is_bound)

    def test_get_sign_up_redirects_when_logged_in(self):
        self.client.login(username=self.user.username, password="Password123")
        response = self.client.get(self.url, follow=True)
        redirect_url = reverse("dashboard")
        self.assertRedirects(
            response, redirect_url, status_code=302, target_status_code=200
        )
        self.assertTemplateUsed(response, "app/dashboard.html")
        self.assertTrue(self._is_logged_in())

    def test_post_sign_up_redirects_when_logged_in(self):
        self.client.login(username=self.user.username, password="Password123")
        before_count = User.objects.count()
        response = self.client.post(self.url, self.form_input, follow=True)
        after_count = User.objects.count()
        self.assertEqual(after_count, before_count)
        redirect_url = reverse("dashboard")
        self.assertRedirects(
            response, redirect_url, status_code=302, target_status_code=200
        )
        self.assertTemplateUsed(response, "app/dashboard.html")
        self.assertTrue(self._is_logged_in())

    def test_succesful_sign_up(self):
        before_count = User.objects.count()
        response = self.client.post(self.url, self.form_input, follow=True)
        after_count = User.objects.count()
        self.assertEqual(after_count, before_count + 1)
        response_url = reverse("dashboard")
        self.assertRedirects(
            response, response_url, status_code=302, target_status_code=200
        )
        self.assertTemplateUsed(response, "app/dashboard.html")
        user = User.objects.get(username="janedoe")
        self.assertEqual(user.first_name, "Jane")
        self.assertEqual(user.last_name, "Doe")
        self.assertEqual(user.email, "janedoe@example.org")
        self.assertTrue(user.check_password("Password123"))
        self.assertTrue(self._is_logged_in())

    def test_unsuccesful_sign_up(self):
        self.form_input["password_confirmation"] = "WrongPassword"
        before_count = User.objects.count()
        response = self.client.post(self.url, self.form_input)
        after_count = User.objects.count()
        self.assertEqual(after_count, before_count)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "auth/sign_up.html")
        form = response.context["form"]
        self.assertTrue(isinstance(form, SignUpForm))
        self.assertTrue(form.is_bound)
        self.assertFalse(self._is_logged_in())

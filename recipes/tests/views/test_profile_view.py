from django.test import TestCase
from django.urls import reverse
from recipes.models import User
from recipes.forms import UserForm
from recipes.tests.helpers import reverse_with_next

class ProfileViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            'johndoe',
            first_name='John',
            last_name='Doe',
            email='johndoe@example.org',
            password='Password123',
            bio='Bio'
        )
        self.url = reverse('profile')

    def test_profile_url(self):
        self.assertEqual(self.url, '/profile/')

    def test_get_profile(self):
        self.client.login(email=self.user.email, password='Password123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profile/profile.html')
        form = response.context['form']
        self.assertTrue(isinstance(form, UserForm))
        self.assertEqual(form.instance, self.user)

    def test_get_profile_redirects_when_not_logged_in(self):
        response = self.client.get(self.url)
        redirect_url = reverse_with_next('log_in', self.url)
        self.assertRedirects(response, redirect_url, status_code=302, target_status_code=200)

    def test_succesful_profile_update(self):
        self.client.login(email=self.user.email, password='Password123')
        form_input = {
            'first_name': 'NewFirst',
            'last_name': 'NewLast',
            'username': 'newusername',
            'email': 'newemail@example.org',
            'bio': 'New Bio'
        }
        response = self.client.post(self.url, form_input)
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'NewFirst')
        self.assertEqual(self.user.last_name, 'NewLast')
        self.assertEqual(self.user.username, 'newusername')
        self.assertEqual(self.user.email, 'newemail@example.org')
        self.assertEqual(self.user.bio, 'New Bio')

    def test_unsuccesful_profile_update(self):
        self.client.login(email=self.user.email, password='Password123')
        form_input = {
            'first_name': 'NewFirst',
            'last_name': 'NewLast',
            'username': '',
            'email': 'newemail@example.org',
            'bio': 'New Bio'
        }
        response = self.client.post(self.url, form_input)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profile/profile.html')
        form = response.context['form']
        self.assertTrue(isinstance(form, UserForm))
        self.assertTrue(form.is_bound)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'johndoe')
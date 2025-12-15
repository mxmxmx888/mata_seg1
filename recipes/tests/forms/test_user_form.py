from django.test import TestCase
from recipes.forms import UserForm
from recipes.models import User

class UserFormTestCase(TestCase):
    def setUp(self):
        self.form_input = {
            'first_name': 'Jane',
            'last_name': 'Doe',
            'username': 'janedoe',
            'email': 'janedoe@example.org',
            'bio': 'Test bio'
        }

    def test_valid_user_form(self):
        form = UserForm(data=self.form_input)
        self.assertTrue(form.is_valid())

    def test_form_has_necessary_fields(self):
        form = UserForm()
        self.assertIn('first_name', form.fields)
        self.assertIn('last_name', form.fields)
        self.assertIn('username', form.fields)
        self.assertIn('email', form.fields)
        self.assertIn('bio', form.fields)

    def test_form_uses_model_validation(self):
        self.form_input['username'] = ''
        form = UserForm(data=self.form_input)
        self.assertFalse(form.is_valid())
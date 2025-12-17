from django import forms
from django.test import TestCase
from recipes.forms import UserForm
from recipes.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

class UserFormTestCase(TestCase):

    fixtures = [
        'recipes/tests/fixtures/default_user.json'
    ]

    def setUp(self):
        self.form_input = {
            'first_name': 'Jane',
            'last_name': 'Doe',
            'username': 'janedoe',
            'email': 'janedoe-new@example.org',
            'is_private': False,
            'remove_avatar': False,
        }

    def test_form_has_necessary_fields(self):
        form = UserForm()
        self.assertIn('first_name', form.fields)
        self.assertIn('last_name', form.fields)
        self.assertIn('username', form.fields)
        self.assertIn('email', form.fields)
        self.assertIn('avatar', form.fields)
        self.assertIn('remove_avatar', form.fields)
        email_field = form.fields['email']
        self.assertTrue(isinstance(email_field, forms.EmailField))
        self.assertTrue(isinstance(form.fields['avatar'], forms.ImageField))
        self.assertTrue(isinstance(form.fields['remove_avatar'], forms.BooleanField))

    def test_valid_user_form(self):
        form = UserForm(data=self.form_input)
        self.assertTrue(form.is_valid())

    def test_form_uses_model_validation(self):
        self.form_input['username'] = 'x!'
        form = UserForm(data=self.form_input)
        self.assertFalse(form.is_valid())

    def test_form_must_save_correctly(self):
        user = User.objects.get(username='@johndoe')
        form = UserForm(instance=user, data=self.form_input)
        before_count = User.objects.count()
        self.assertTrue(form.is_valid())
        form.save()
        after_count = User.objects.count()
        self.assertEqual(after_count, before_count)
        self.assertEqual(user.username, 'janedoe')
        self.assertEqual(user.first_name, 'Jane')
        self.assertEqual(user.last_name, 'Doe')
        self.assertEqual(user.email, 'janedoe-new@example.org')

    def test_user_form_sets_new_avatar_without_removal(self):
        user = User.objects.get(username='@johndoe')
        png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\nIDATx\x9cc``\x00\x00\x00\x02\x00\x01\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
        upload = SimpleUploadedFile("new.png", png_bytes, content_type="image/png")
        form = UserForm(instance=user, data=self.form_input)
        form.is_valid()
        form.cleaned_data["avatar"] = upload
        updated = form.save(commit=False)
        self.assertEqual(updated.avatar, upload)

    def test_existing_avatar_replaced_and_deleted(self):
        class DummyAvatar:
            def __init__(self):
                self.deleted = False
            def delete(self, save=False):
                self.deleted = True
        user = User.objects.get(username='@johndoe')
        dummy = DummyAvatar()
        user.avatar = dummy
        upload = SimpleUploadedFile("new.png", b"img", content_type="image/png")
        form = UserForm(instance=user, data=self.form_input)
        form.is_valid()
        form.cleaned_data["avatar"] = upload
        updated = form.save(commit=False)
        self.assertTrue(dummy.deleted)
        self.assertEqual(updated.avatar, upload)

    def test_user_form_remove_avatar_when_empty(self):
        user = User.objects.get(username='@johndoe')
        form = UserForm(instance=user, data={**self.form_input, "remove_avatar": True})
        self.assertTrue(form.is_valid())
        saved = form.save()
        self.assertFalse(saved.avatar)

    def test_user_form_commit_false_keeps_instance(self):
        user = User.objects.get(username='@johndoe')
        form = UserForm(instance=user, data=self.form_input)
        form.is_valid()
        partial = form.save(commit=False)
        self.assertEqual(partial.username, 'janedoe')

    def test_user_form_remove_avatar_deletes_existing(self):
        user = User.objects.get(username='@johndoe')
        user.avatar = "avatars/old.png"
        form = UserForm(instance=user, data={**self.form_input, "remove_avatar": True})
        form.is_valid()
        cleaned = form.save()
        self.assertFalse(cleaned.avatar)

    def test_remove_avatar_calls_delete_when_present(self):
        class DummyAvatar:
            def __init__(self):
                self.deleted = 0
            def delete(self, save=False):
                self.deleted += 1
        user = User.objects.get(username='@johndoe')
        avatar = DummyAvatar()
        user.avatar = avatar
        form = UserForm(instance=user, data={**self.form_input, "remove_avatar": True})
        self.assertTrue(form.is_valid())
        form.save()
        self.assertGreaterEqual(avatar.deleted, 1)

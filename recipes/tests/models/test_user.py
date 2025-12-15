from django.test import TestCase
from django.core.exceptions import ValidationError
from recipes.models import User

class UserModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            'johndoe',
            first_name='John',
            last_name='Doe',
            email='johndoe@example.org',
            password='Password123',
            bio='The quick brown fox jumps over the lazy dog.'
        )

    def _assert_user_is_valid(self):
        try:
            self.user.full_clean()
        except (ValidationError):
            self.fail('Test user should be valid')

    def _assert_user_is_invalid(self):
        with self.assertRaises(ValidationError):
            self.user.full_clean()

    def test_valid_user(self):
        self._assert_user_is_valid()

    def test_username_can_be_30_characters_long(self):
        self.user.username = 'x' * 30
        self._assert_user_is_valid()

    def test_username_cannot_be_over_30_characters_long(self):
        self.user.username = 'x' * 31
        self._assert_user_is_invalid()

    def test_username_must_be_unique(self):
        User.objects.create_user(
            'janedoe',
            first_name='Jane',
            last_name='Doe',
            email='janedoe@example.org',
            password='Password123',
            bio='The quick brown fox jumps over the lazy dog.'
        )
        self.user.username = 'janedoe'
        self._assert_user_is_invalid()

    def test_username_may_contain_numbers(self):
        self.user.username = 'j0hndoe2'
        self._assert_user_is_valid()

    def test_first_name_must_not_be_blank(self):
        self.user.first_name = ''
        self._assert_user_is_invalid()

    def test_first_name_need_not_be_unique(self):
        second_user = User.objects.create_user(
            'janedoe',
            first_name='John',
            last_name='Doe',
            email='janedoe@example.org',
            password='Password123',
            bio='The quick brown fox jumps over the lazy dog.'
        )
        self.user.first_name = second_user.first_name
        self._assert_user_is_valid()

    def test_first_name_may_contain_50_characters(self):
        self.user.first_name = 'x' * 50
        self._assert_user_is_valid()

    def test_first_name_cannot_contain_more_than_50_characters(self):
        self.user.first_name = 'x' * 51
        self._assert_user_is_invalid()

    def test_last_name_must_not_be_blank(self):
        self.user.last_name = ''
        self._assert_user_is_invalid()

    def test_last_name_need_not_be_unique(self):
        second_user = User.objects.create_user(
            'janedoe',
            first_name='Jane',
            last_name='Doe',
            email='janedoe@example.org',
            password='Password123',
            bio='The quick brown fox jumps over the lazy dog.'
        )
        self.user.last_name = second_user.last_name
        self._assert_user_is_valid()

    def test_last_name_may_contain_50_characters(self):
        self.user.last_name = 'x' * 50
        self._assert_user_is_valid()

    def test_last_name_cannot_contain_more_than_50_characters(self):
        self.user.last_name = 'x' * 51
        self._assert_user_is_invalid()

    def test_email_must_not_be_blank(self):
        self.user.email = ''
        self._assert_user_is_invalid()

    def test_email_must_be_unique(self):
        User.objects.create_user(
            'janedoe',
            first_name='Jane',
            last_name='Doe',
            email='janedoe@example.org',
            password='Password123',
            bio='The quick brown fox jumps over the lazy dog.'
        )
        self.user.email = 'janedoe@example.org'
        self._assert_user_is_invalid()

    def test_bio_may_be_blank(self):
        self.user.bio = ''
        self._assert_user_is_valid()

    def test_bio_need_not_be_unique(self):
        second_user = User.objects.create_user(
            'janedoe',
            first_name='Jane',
            last_name='Doe',
            email='janedoe@example.org',
            password='Password123',
            bio='The quick brown fox jumps over the lazy dog.'
        )
        self.user.bio = second_user.bio
        self._assert_user_is_valid()

    def test_bio_may_contain_500_characters(self):
        self.user.bio = 'x' * 500
        self._assert_user_is_valid()

    def test_bio_cannot_contain_more_than_500_characters(self):
        self.user.bio = 'x' * 600
        with self.assertRaises(ValidationError):
            self.user.full_clean()

    def test_remove_avatar_flag_clears_avatar(self):
        self.user.avatar = 'avatars/test.jpg'
        self.user.save()
        self.user.save(remove_avatar=True)
        self.user.refresh_from_db()
        self.assertFalse(bool(self.user.avatar))
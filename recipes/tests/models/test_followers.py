from django.test import TestCase
from django.db import IntegrityError, transaction

from recipes.models.followers import Follower
from recipes.tests.test_utils import make_user


class FollowerModelTestCase(TestCase):

    def setUp(self):
        self.user_a = make_user(username="usera")
        self.user_b = make_user(username="userb")

    def test_user_can_follow_another_user(self):
        follower = Follower.objects.create(
            follower=self.user_a,
            author=self.user_b,
        )

        self.assertEqual(follower.follower, self.user_a)
        self.assertEqual(follower.author, self.user_b)
        self.assertEqual(Follower.objects.count(), 1)

    def test_duplicate_follow_not_allowed(self):
        Follower.objects.create(
            follower=self.user_a,
            author=self.user_b,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Follower.objects.create(
                    follower=self.user_a,
                    author=self.user_b,
                )

    def test_can_check_if_user_is_following(self):
        Follower.objects.create(
            follower=self.user_a,
            author=self.user_b,
        )

        is_following = Follower.objects.filter(
            follower=self.user_a,
            author=self.user_b,
        ).exists()

        self.assertTrue(is_following)

    def test_can_get_all_followers_of_user(self):
        Follower.objects.create(
            follower=self.user_a,
            author=self.user_b,
        )

        followers = Follower.objects.filter(author=self.user_b)
        self.assertEqual(followers.count(), 1)
        self.assertEqual(followers.first().follower, self.user_a)

    def test_string_representation(self):
        follower = Follower.objects.create(
            follower=self.user_a,
            author=self.user_b,
        )

        self.assertIsInstance(str(follower), str)
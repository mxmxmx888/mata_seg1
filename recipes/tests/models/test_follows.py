from django.test import TestCase
from django.db import IntegrityError

from recipes.models.follows import Follows
from recipes.tests.helpers import make_user


class FollowsModelTestCase(TestCase):
    def setUp(self):
        self.user_a = make_user(username="@usera")
        self.user_b = make_user(username="@userb")
        self.user_c = make_user(username="@userc")

    def test_user_can_follow_another_user(self):
        follow = Follows.objects.create(author=self.user_a, followee=self.user_b)

        self.assertEqual(follow.author, self.user_a)
        self.assertEqual(follow.followee, self.user_b)
        self.assertEqual(Follows.objects.count(), 1)

    def test_duplicate_follow_not_allowed(self):
        Follows.objects.create(author=self.user_a, followee=self.user_b)

        with self.assertRaises(IntegrityError):
            Follows.objects.create(author=self.user_a, followee=self.user_b)

    def test_can_get_all_followees_for_author(self):
        Follows.objects.create(author=self.user_a, followee=self.user_b)
        Follows.objects.create(author=self.user_a, followee=self.user_c)

        followee_ids = list(
            Follows.objects.filter(author=self.user_a).values_list("followee_id", flat=True)
        )

        self.assertCountEqual(followee_ids, [self.user_b.id, self.user_c.id])

    def test_can_get_all_authors_following_user(self):
        Follows.objects.create(author=self.user_a, followee=self.user_c)
        Follows.objects.create(author=self.user_b, followee=self.user_c)

        author_ids = list(
            Follows.objects.filter(followee=self.user_c).values_list("author_id", flat=True)
        )

        self.assertCountEqual(author_ids, [self.user_a.id, self.user_b.id])

    def test_can_check_if_author_follows_user(self):
        self.assertFalse(
            Follows.objects.filter(author=self.user_a, followee=self.user_b).exists()
        )

        Follows.objects.create(author=self.user_a, followee=self.user_b)

        self.assertTrue(
            Follows.objects.filter(author=self.user_a, followee=self.user_b).exists()
        )
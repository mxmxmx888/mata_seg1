from django.db import IntegrityError
from django.test import TestCase

from recipes.models.close_friend import CloseFriend
from recipes.tests.test_utils import make_user


class CloseFriendModelTestCase(TestCase):
    def setUp(self):
        self.owner = make_user(username="@owner")
        self.friend = make_user(username="@friend")

    def test_owner_can_add_close_friend(self):
        cf = CloseFriend.objects.create(owner=self.owner, friend=self.friend)
        self.assertEqual(cf.owner, self.owner)
        self.assertEqual(cf.friend, self.friend)

    def test_duplicate_close_friend_not_allowed(self):
        CloseFriend.objects.create(owner=self.owner, friend=self.friend)
        with self.assertRaises(IntegrityError):
            CloseFriend.objects.create(owner=self.owner, friend=self.friend)

    def test_cannot_add_self_as_close_friend(self):
        
        with self.assertRaises(IntegrityError):
            CloseFriend.objects.create(owner=self.owner, friend=self.owner)

    def test_can_query_close_friends_for_owner(self):
        CloseFriend.objects.create(owner=self.owner, friend=self.friend)
        qs = CloseFriend.objects.filter(owner=self.owner)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().friend, self.friend)

    def test_string_representation(self):
        cf = CloseFriend.objects.create(owner=self.owner, friend=self.friend)
        s = str(cf)
        self.assertIn("CloseFriend(", s)
        self.assertIn(str(self.owner.id), s)
        self.assertIn(str(self.friend.id), s)
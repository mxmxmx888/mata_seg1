from django.db import IntegrityError
from django.test import TestCase
from recipes.models import User, FollowRequest

class FollowRequestModelTestCase(TestCase):
    fixtures = [
        "recipes/tests/fixtures/default_user.json",
        "recipes/tests/fixtures/other_users.json",
    ]

    def setUp(self):
        self.requester = User.objects.get(username="@johndoe")
        self.target = User.objects.get(username="@janedoe")

    def test_str_includes_ids_and_status(self):
        fr = FollowRequest.objects.create(requester=self.requester, target=self.target)
        expected = f"FollowRequest({self.requester.id} -> {self.target.id}, pending)"
        self.assertEqual(str(fr), expected)

    def test_unique_constraint_blocks_duplicate(self):
        FollowRequest.objects.create(requester=self.requester, target=self.target)
        with self.assertRaises(IntegrityError):
            FollowRequest.objects.create(requester=self.requester, target=self.target)

    def test_cannot_request_self(self):
        with self.assertRaises(IntegrityError):
            FollowRequest.objects.create(requester=self.requester, target=self.requester)

from django.test import TestCase

from recipes.repos.user_repo import UserRepo
from recipes.tests.helpers import make_user


class UserRepoTests(TestCase):
    def setUp(self):
        self.repo = UserRepo()
        self.u1 = make_user(username="@alpha")
        self.u2 = make_user(username="@bravo")

    def test_list_ids_returns_all_user_ids(self):
        ids = self.repo.list_ids()
        self.assertEqual(set(ids), {self.u1.id, self.u2.id})

    def test_get_by_id_fetches_user(self):
        user = self.repo.get_by_id(self.u1.id)
        self.assertEqual(user.id, self.u1.id)
        self.assertEqual(user.username, self.u1.username)

    def test_get_by_username_fetches_user(self):
        user = self.repo.get_by_username(self.u2.username)
        self.assertEqual(user.id, self.u2.id)
        self.assertEqual(user.username, self.u2.username)

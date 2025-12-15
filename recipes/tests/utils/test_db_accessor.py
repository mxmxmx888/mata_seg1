from django.test import TestCase
from django.core.exceptions import ObjectDoesNotExist

from recipes.db_accessor import DB_Accessor  # adjust if your path differs
from recipes.models import User


class DBAccessorTestCase(TestCase):
    def setUp(self):
        self.accessor = DB_Accessor(User)

        # create a few users with predictable ordering
        self.u1 = User.objects.create_user(username="@alpha", email="alpha@example.org", password="Password123")
        self.u2 = User.objects.create_user(username="@bravo", email="bravo@example.org", password="Password123")
        self.u3 = User.objects.create_user(username="@charlie", email="charlie@example.org", password="Password123")

    def test_create_creates_row(self):
        u = self.accessor.create(username="@delta", email="delta@example.org")
        self.assertTrue(User.objects.filter(id=u.id).exists())
        self.assertEqual(u.username, "@delta")

    def test_get_returns_single_object(self):
        u = self.accessor.get(id=self.u2.id)
        self.assertEqual(u.id, self.u2.id)
        self.assertEqual(u.username, "@bravo")

    def test_get_raises_if_missing(self):
        with self.assertRaises(ObjectDoesNotExist):
            self.accessor.get(username="@doesnotexist")

    def test_list_returns_queryset_by_default(self):
        qs = self.accessor.list()
        self.assertTrue(hasattr(qs, "model"))
        self.assertEqual(qs.model, User)
        self.assertEqual(qs.count(), 3)

    def test_list_filters(self):
        qs = self.accessor.list(filters={"username": "@bravo"})
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().id, self.u2.id)

    def test_list_order_by(self):
        qs = self.accessor.list(order_by=("username",))
        self.assertEqual(list(qs.values_list("username", flat=True)), ["@alpha", "@bravo", "@charlie"])

        qs_desc = self.accessor.list(order_by=("-username",))
        self.assertEqual(list(qs_desc.values_list("username", flat=True)), ["@charlie", "@bravo", "@alpha"])

    def test_list_limit_and_offset(self):
        qs = self.accessor.list(order_by=("username",), limit=2, offset=0)
        self.assertEqual(list(qs.values_list("username", flat=True)), ["@alpha", "@bravo"])

        qs2 = self.accessor.list(order_by=("username",), limit=2, offset=1)
        self.assertEqual(list(qs2.values_list("username", flat=True)), ["@bravo", "@charlie"])

    def test_list_offset_without_limit(self):
        qs = self.accessor.list(order_by=("username",), offset=2)
        self.assertEqual(list(qs.values_list("username", flat=True)), ["@charlie"])

    def test_list_as_dict_returns_list_of_dicts(self):
        rows = self.accessor.list(order_by=("username",), as_dict=True)
        self.assertIsInstance(rows, list)
        self.assertTrue(all(isinstance(r, dict) for r in rows))
        self.assertEqual([r["username"] for r in rows], ["@alpha", "@bravo", "@charlie"])

    def test_update_returns_updated_count_and_updates(self):
        updated = self.accessor.update({"id": self.u1.id}, first_name="A")
        self.assertEqual(updated, 1)
        self.u1.refresh_from_db()
        self.assertEqual(self.u1.first_name, "A")

    def test_update_returns_zero_if_no_match(self):
        updated = self.accessor.update({"username": "@nope"}, first_name="X")
        self.assertEqual(updated, 0)

    def test_delete_returns_deleted_count(self):
        deleted = self.accessor.delete(id=self.u3.id)
        self.assertEqual(deleted, 1)
        self.assertFalse(User.objects.filter(id=self.u3.id).exists())

    def test_delete_returns_zero_if_missing(self):
        deleted = self.accessor.delete(username="@missing")
        self.assertEqual(deleted, 0)
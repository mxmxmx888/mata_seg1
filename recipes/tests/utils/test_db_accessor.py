from django.test import TestCase
from recipes.db_accessor import DB_Accessor
from recipes.models import RecipePost, User


class DBAccessorTests(TestCase):

    fixtures = [
        "recipes/tests/fixtures/default_user.json",
        "recipes/tests/fixtures/other_users.json",
    ]

    def setUp(self):
        self.user = User.objects.get(username="@johndoe")
        self.obj1 = RecipePost.objects.create(
            author=self.user,
            title="Soup",
            description="veg",
            category="dinner",
        )
        self.obj2 = RecipePost.objects.create(
            author=self.user,
            title="Cake",
            description="sweet",
            category="dessert",
        )

        self.repo = DB_Accessor(RecipePost)

    # ---------- list() ----------

    def test_list_default_returns_queryset(self):
        qs = self.repo.list()
        self.assertEqual(qs.count(), 2)

    def test_list_filters(self):
        qs = self.repo.list(filters={"title": "Soup"})
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().title, "Soup")

    def test_list_order_by(self):
        qs = self.repo.list(order_by=["title"])
        titles = list(qs.values_list("title", flat=True))
        self.assertEqual(titles, ["Cake", "Soup"])

    def test_list_limit_and_offset(self):
        qs = self.repo.list(limit=1)
        self.assertEqual(qs.count(), 1)

        qs_offset = self.repo.list(limit=1, offset=1)
        self.assertEqual(qs_offset.count(), 1)

    def test_list_offset_no_limit(self):
        qs = self.repo.list(offset=1)
        self.assertEqual(qs.count(), 1)

    def test_list_as_dict(self):
        result = self.repo.list(as_dict=True)
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], dict)

    def test_list_empty_slice_returns_none_queryset(self):
        qs = self.repo.list(limit=1, offset=10)
        self.assertEqual(qs.count(), 0)

    # ---------- get() ----------

    def test_get(self):
        obj = self.repo.get(id=self.obj1.id)
        self.assertEqual(obj, self.obj1)

    # ---------- create() ----------

    def test_create(self):
        created = self.repo.create(
            author=self.user,
            title="New",
            description="X",
            category="test",
        )
        self.assertEqual(created.title, "New")
        self.assertEqual(RecipePost.objects.count(), 3)

    # ---------- update() ----------

    def test_update(self):
        count = self.repo.update({"id": self.obj1.id}, title="Updated")
        self.assertEqual(count, 1)
        self.obj1.refresh_from_db()
        self.assertEqual(self.obj1.title, "Updated")

    # ---------- delete() ----------

    def test_delete(self):
        count = self.repo.delete(id=self.obj2.id)
        self.assertEqual(count, 1)
        self.assertFalse(RecipePost.objects.filter(id=self.obj2.id).exists())

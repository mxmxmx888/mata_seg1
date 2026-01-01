from django.test import RequestFactory, TestCase

from recipes.models import Favourite, FavouriteItem, RecipePost, User, Comment
from recipes.services.recipe_posts import RecipePostService


class RecipePostServiceTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="@rps",
            email="rps@example.com",
            password="Password123",
        )
        self.post = RecipePost.objects.create(
            author=self.user,
            title="Title",
            description="Desc",
        )
        self.service = RecipePostService()

    def test_comments_page_paginates(self):
        for i in range(3):
            Comment.objects.create(recipe_post=self.post, user=self.user, text=f"c{i}")
        request = self.factory.get("/?comments_page=1")
        page, has_more, page_number = self.service.comments_page(self.post, request, page_size=2)
        self.assertEqual(len(page), 2)
        self.assertTrue(has_more)
        self.assertEqual(page_number, 1)

    def test_saved_posts_for_user_deduplicates(self):
        fav1 = Favourite.objects.create(user=self.user, name="A")
        fav2 = Favourite.objects.create(user=self.user, name="B")
        FavouriteItem.objects.create(favourite=fav1, recipe_post=self.post)
        FavouriteItem.objects.create(favourite=fav2, recipe_post=self.post)

        posts = self.service.saved_posts_for_user(self.user)

        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0], self.post)

    def test_comments_page_handles_invalid_page_number(self):
        Comment.objects.create(recipe_post=self.post, user=self.user, text="c1")
        Comment.objects.create(recipe_post=self.post, user=self.user, text="c2")
        request = self.factory.get("/?comments_page=bad")

        page, has_more, page_number = self.service.comments_page(self.post, request, page_size=1)

        self.assertEqual(page_number, 1)
        self.assertTrue(has_more)
        self.assertEqual(len(page), 1)

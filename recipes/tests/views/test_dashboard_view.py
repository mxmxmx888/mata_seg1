from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from recipes.models import Ingredient, Follower
from recipes.tests.helpers import make_recipe_post, make_user
from recipes.views import dashboard_view


class DashboardSearchViewTests(TestCase):
    def setUp(self):
        self.user = make_user(username="searcher")
        self.client.login(username=self.user.username, password="Password123")
        self.url = reverse("dashboard")

    def test_search_matches_title_and_description(self):
        matching = make_recipe_post(
            author=self.user,
            title="Garlic Butter Pasta",
            description="A quick pasta dinner",
        )
        non_matching = make_recipe_post(
            author=self.user,
            title="Tomato Soup",
            description="Cozy soup for winter",
        )

        response = self.client.get(self.url, {"q": "pasta", "mode": "search"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, matching.title)
        self.assertNotContains(response, non_matching.title)

    def test_anonymous_gets_logged_out_discover_page(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "auth/discover_logged_out.html")

    def test_normalise_tags_handles_strings_lists_and_none(self):
        self.assertEqual(dashboard_view._normalise_tags(None), [])
        self.assertEqual(dashboard_view._normalise_tags("A, b ,"), ["a", "b"])
        self.assertEqual(dashboard_view._normalise_tags([" X ", ""]), ["x"])

    def test_filter_posts_by_prep_time_bounds(self):
        class Obj:
            def __init__(self, prep):
                self.prep_time_min = prep

        posts = [Obj(5), Obj(10), Obj(None)]
        self.assertEqual(len(dashboard_view._filter_posts_by_prep_time(posts, 6, None)), 1)
        self.assertEqual(len(dashboard_view._filter_posts_by_prep_time(posts, None, 6)), 1)

    def test_normalise_tags_unknown_type_returns_empty(self):
        self.assertEqual(dashboard_view._normalise_tags(123), [])

    def test_score_post_without_published_date(self):
        post = make_recipe_post(author=self.user, title="No date", published=False, tags=["x"], saved_count=2)
        score = dashboard_view._score_post_for_user(post, ["x"])
        # score includes tag bonus + saved_count
        self.assertGreaterEqual(score, 5)

    def test_get_for_you_posts_scores_and_orders(self):
        # user preference tags inferred from favourites/likes
        pref_post = make_recipe_post(author=self.user, tags=["pasta"], saved_count=5)
        other_post = make_recipe_post(author=self.user, tags=["soup"], saved_count=0)
        # set preference by saving the first post
        fav = self.user.favourites.create(name="favourites")
        fav.items.create(recipe_post=pref_post)
        dashboard_view.Like.objects.create(user=self.user, recipe_post=pref_post)

        posts = dashboard_view._get_for_you_posts(self.user, seed=123)
        self.assertEqual(set(p.id for p in posts), {pref_post.id, other_post.id})
        self.assertGreater(
            dashboard_view._score_post_for_user(pref_post, ["pasta"]),
            dashboard_view._score_post_for_user(other_post, ["pasta"]),
        )

    def test_get_for_you_posts_filters_query(self):
        match = make_recipe_post(author=self.user, title="Garlic Bread")
        make_recipe_post(author=self.user, title="Something else")
        posts = dashboard_view._get_for_you_posts(self.user, query="garlic", seed=0)
        self.assertEqual([p.id for p in posts], [match.id])

    def test_get_following_posts_returns_only_followed(self):
        author = make_user(username="author1")
        Follower.objects.create(follower=self.user, author=author)
        post = make_recipe_post(author=author, title="From followed")
        make_recipe_post(author=self.user, title="Mine")

        posts = dashboard_view._get_following_posts(self.user)
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].title, "From followed")

    def test_get_following_posts_filters_query(self):
        author = make_user(username="author2")
        Follower.objects.create(follower=self.user, author=author)
        make_recipe_post(author=author, title="Pizza Night")
        make_recipe_post(author=author, title="Salad Bowl")
        posts = dashboard_view._get_following_posts(self.user, query="pizza")
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].title, "Pizza Night")

    def test_search_users_no_query_returns_empty(self):
        self.assertEqual(dashboard_view._search_users("", limit=5), [])

    def test_dashboard_for_you_ajax_returns_json(self):
        make_recipe_post(author=self.user, title="A")
        self.client.login(username=self.user.username, password="Password123")
        url = self.url

        response = self.client.get(url, {"for_you_ajax": "1", "for_you_offset": "-5"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("html", payload)
        self.assertIn("has_more", payload)
        # seed should have been set in session
        self.assertIn("for_you_seed", self.client.session)

    def test_dashboard_user_search_scope(self):
        target = make_user(username="alice")
        self.client.login(username=self.user.username, password="Password123")

        response = self.client.get(self.url, {"q": "ali", "scope": "users", "mode": "search"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(target, response.context["users_results"])

    def test_dashboard_recipe_search_ajax_returns_json(self):
        for i in range(20):
            make_recipe_post(author=self.user, title=f"Post {i}")
        self.client.login(username=self.user.username, password="Password123")

        response = self.client.get(self.url, {"mode": "search", "ajax": "1"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("html", payload)
        self.assertTrue(payload["has_next"])

    def test_dashboard_filters_by_ingredients_and_prep_time(self):
        # post with allowed ingredient and low prep time
        good = make_recipe_post(author=self.user, title="Allowed", prep_time_min=5, cook_time_min=5)
        Ingredient.objects.create(recipe_post=good, name="garlic", position=1)
        # post that should be filtered out
        bad = make_recipe_post(author=self.user, title="Filtered", prep_time_min=30, cook_time_min=5)
        Ingredient.objects.create(recipe_post=bad, name="onion", position=1)

        self.client.login(username=self.user.username, password="Password123")
        response = self.client.get(
            self.url,
            {
                "have_ingredients": "garlic",
                "min_prep": "abc",  # ignored
                "max_prep": "xyz",  # ignored by except block
                "mode": "search",
            },
        )
        self.assertEqual(response.status_code, 200)
        posts = response.context["popular_recipes"]
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].title, "Allowed")

    def test_dashboard_handles_invalid_scope_and_page(self):
        make_recipe_post(author=self.user, title="Visible")
        self.client.login(username=self.user.username, password="Password123")
        response = self.client.get(self.url, {"scope": "invalid", "page": "-2"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["scope"], "recipes")

    def test_dashboard_sort_popular_and_oldest(self):
        older = make_recipe_post(
            author=self.user,
            title="Older",
            prep_time_min=1,
            cook_time_min=1,
            saved_count=5,
            published=False,
        )
        recent = make_recipe_post(
            author=self.user,
            title="Recent",
            prep_time_min=1,
            cook_time_min=1,
            saved_count=1,
            published=False,
        )
        older.published_at = timezone.now() - timezone.timedelta(days=2)
        older.save(update_fields=["published_at"])
        recent.published_at = timezone.now()
        recent.save(update_fields=["published_at"])
        self.client.login(username=self.user.username, password="Password123")

        res_popular = self.client.get(self.url, {"sort": "popular"})
        self.assertEqual(res_popular.status_code, 200)
        popular_titles = [p.title for p in res_popular.context["popular_recipes"]]
        self.assertEqual(popular_titles[0], "Older")

        res_oldest = self.client.get(self.url, {"sort": "oldest"})
        self.assertEqual(res_oldest.status_code, 200)
        oldest_titles = [p.title for p in res_oldest.context["popular_recipes"]]
        self.assertEqual(oldest_titles[0], "Older")

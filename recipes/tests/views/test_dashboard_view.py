from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from recipes.models import Ingredient, Follower, Like
from recipes.tests.test_utils import make_recipe_post, make_user
from recipes.views import dashboard_view

class DashboardSearchViewTests(TestCase):
    def setUp(self):
        self.user = make_user(username="searcher")
        self.feed_service = dashboard_view.feed_service
        self.client.login(username=self.user.username, password="Password123")
        self.url = reverse("dashboard")
        self.make_published = lambda title, days_ago, saves: self._publish(
            title=title,
            days_ago=days_ago,
            saved_count=saves,
        )

    def _publish(self, title, days_ago, saved_count):
        post = make_recipe_post(
            author=self.user,
            title=title,
            prep_time_min=1,
            cook_time_min=1,
            saved_count=saved_count,
            published=False,
        )
        post.published_at = timezone.now() - timezone.timedelta(days=days_ago)
        post.save(update_fields=["published_at"])
        return post

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
        self.assertEqual(self.feed_service.normalise_tags(None), [])
        self.assertEqual(self.feed_service.normalise_tags("A, b ,"), ["a", "b"])
        self.assertEqual(self.feed_service.normalise_tags([" X ", ""]), ["x"])

    def test_filter_posts_by_prep_time_bounds(self):
        class Obj:
            def __init__(self, prep):
                self.prep_time_min = prep

        posts = [Obj(5), Obj(10), Obj(None)]
        self.assertEqual(len(self.feed_service.filter_posts_by_prep_time(posts, 6, None)), 1)
        self.assertEqual(len(self.feed_service.filter_posts_by_prep_time(posts, None, 6)), 1)

    def test_filter_posts_by_prep_time_handles_missing_and_none_bounds(self):
        class Obj:
            def __init__(self, prep):
                self.prep_time_min = prep
        posts = [Obj("bad"), Obj(3)]
        result = self.feed_service.filter_posts_by_prep_time(posts, None, None)
        self.assertEqual(len(result), 2)
        filtered = self.feed_service.filter_posts_by_prep_time(posts, 1, 5)
        self.assertEqual(filtered, [posts[1]])

    def test_score_post_no_tag_bonus(self):
        post = make_recipe_post(author=self.user, tags=["x"], saved_count=2, published=False)
        score = self.feed_service.score_post_for_user(post, ["other"])
        self.assertGreaterEqual(score, 2)

    def test_user_preference_tags_dedupes(self):
        liked = make_recipe_post(author=self.user, tags=["pasta", "pasta"])
        Like.objects.create(user=self.user, recipe_post=liked)
        tags = self.feed_service.user_preference_tags(self.user)
        self.assertEqual(tags, ["pasta"])

    def test_normalise_tags_unknown_type_returns_empty(self):
        self.assertEqual(self.feed_service.normalise_tags(123), [])

    def test_score_post_without_published_date(self):
        post = make_recipe_post(author=self.user, title="No date", published=False, tags=["x"], saved_count=2)
        score = self.feed_service.score_post_for_user(post, ["x"])
        self.assertGreaterEqual(score, 5) #score includes tag bonus + saved_count

    def test_get_for_you_posts_filters_by_liked_tags_and_excludes_liked(self):
        liked = make_recipe_post(author=self.user, tags=["pasta"])
        match = make_recipe_post(author=self.user, tags=["pasta"])
        non_match = make_recipe_post(author=self.user, tags=["soup"])
        Like.objects.create(user=self.user, recipe_post=liked)

        posts = self.feed_service.for_you_posts(self.user, seed=123)
        self.assertEqual(set(p.id for p in posts), {match.id})
        self.assertNotIn(non_match.id, [p.id for p in posts])

    def test_get_for_you_posts_random_when_no_likes(self):
        first = make_recipe_post(author=self.user, tags=["x"])
        second = make_recipe_post(author=self.user, tags=["y"])

        posts = self.feed_service.for_you_posts(self.user, seed=1)
        self.assertEqual(set(p.id for p in posts), {first.id, second.id})

    def test_get_for_you_posts_for_anonymous_user(self):
        anon = AnonymousUser()
        posts = self.feed_service.for_you_posts(anon, seed=2)
        self.assertIsInstance(posts, list)

    def test_get_for_you_posts_with_likes_but_no_tags_falls_back_to_all(self):
        liked = make_recipe_post(author=self.user, tags=[])
        other = make_recipe_post(author=self.user, tags=["something"])
        Like.objects.create(user=self.user, recipe_post=liked)

        posts = self.feed_service.for_you_posts(self.user, seed=1)
        self.assertEqual(set(p.id for p in posts), {liked.id, other.id})

    def test_get_for_you_posts_with_tag_filter_no_results_falls_back(self):
        liked = make_recipe_post(author=self.user, tags=["pasta"])
        Like.objects.create(user=self.user, recipe_post=liked)
        # Query matches liked post; exclusion removes it, triggering fallback that should return the liked post.
        posts = self.feed_service.for_you_posts(self.user, query="pasta", seed=2, limit=5)
        self.assertEqual([p.id for p in posts], [liked.id])

    def test_get_for_you_posts_filters_query(self):
        match = make_recipe_post(author=self.user, title="Garlic Bread")
        make_recipe_post(author=self.user, title="Something else")
        posts = self.feed_service.for_you_posts(self.user, query="garlic", seed=0)
        self.assertEqual([p.id for p in posts], [match.id])

    def test_get_following_posts_returns_only_followed(self):
        author = make_user(username="author1")
        Follower.objects.create(follower=self.user, author=author)
        post = make_recipe_post(author=author, title="From followed")
        make_recipe_post(author=self.user, title="Mine")

        posts = self.feed_service.following_posts(self.user)
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].title, "From followed")

    def test_get_following_posts_filters_query(self):
        author = make_user(username="author2")
        Follower.objects.create(follower=self.user, author=author)
        make_recipe_post(author=author, title="Pizza Night")
        make_recipe_post(author=author, title="Salad Bowl")
        posts = self.feed_service.following_posts(self.user, query="pizza")
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].title, "Pizza Night")

    def test_search_users_no_query_returns_empty(self):
        self.assertEqual(self.feed_service.search_users("", limit=5), [])

    def test_dashboard_for_you_ajax_returns_json(self):
        make_recipe_post(author=self.user, title="A")
        self.client.login(username=self.user.username, password="Password123")
        url = self.url

        response = self.client.get(url, {"for_you_ajax": "1", "for_you_offset": "-5"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("html", payload)
        self.assertIn("has_more", payload)
        self.assertIn("for_you_seed", self.client.session) #seed should have been set in session

    def test_dashboard_for_you_ajax_reuses_existing_seed(self):
        make_recipe_post(author=self.user, title="Seeded")
        self.client.login(username=self.user.username, password="Password123")
        session = self.client.session
        session["for_you_seed"] = 0.5
        session.save()
        response = self.client.get(self.url, {"for_you_ajax": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session["for_you_seed"], 0.5)

    def test_dashboard_following_ajax_returns_json(self):
        author = make_user(username="followed")
        Follower.objects.create(follower=self.user, author=author)
        make_recipe_post(author=author, title="Followed post")
        self.client.login(username=self.user.username, password="Password123")

        response = self.client.get(self.url, {"following_ajax": "1"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("html", payload)
        self.assertIn("has_more", payload)

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
        good = make_recipe_post(author=self.user, title="Allowed", prep_time_min=5, cook_time_min=5)
        Ingredient.objects.create(recipe_post=good, name="garlic", position=1)
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

    def test_dashboard_filters_by_valid_prep_time(self):
        quick = make_recipe_post(author=self.user, title="Quick", prep_time_min=5, cook_time_min=5)
        slow = make_recipe_post(author=self.user, title="Slow", prep_time_min=50, cook_time_min=5)
        self.client.login(username=self.user.username, password="Password123")
        response = self.client.get(
            self.url,
            {
                "mode": "search",
                "min_prep": "5",
                "max_prep": "15",
            },
        )
        posts = response.context["popular_recipes"]
        self.assertIn(quick, posts)
        self.assertNotIn(slow, posts)

    def test_dashboard_max_prep_only(self):
        ok = make_recipe_post(author=self.user, title="Ok", prep_time_min=2, cook_time_min=2)
        make_recipe_post(author=self.user, title="Too long", prep_time_min=50, cook_time_min=0)
        self.client.login(username=self.user.username, password="Password123")
        resp = self.client.get(self.url, {"mode": "search", "max_prep": "5"})
        titles = [p.title for p in resp.context["popular_recipes"]]
        self.assertIn("Ok", titles)

    def test_dashboard_min_prep_only(self):
        make_recipe_post(author=self.user, title="Short", prep_time_min=1, cook_time_min=0)
        long = make_recipe_post(author=self.user, title="Long", prep_time_min=10, cook_time_min=0)
        self.client.login(username=self.user.username, password="Password123")
        resp = self.client.get(self.url, {"mode": "search", "min_prep": "5"})
        titles = [p.title for p in resp.context["popular_recipes"]]
        self.assertIn(long.title, titles)

    def test_dashboard_handles_invalid_scope_and_page(self):
        make_recipe_post(author=self.user, title="Visible")
        self.client.login(username=self.user.username, password="Password123")
        response = self.client.get(self.url, {"scope": "invalid", "page": "-2"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["scope"], "recipes")

    def test_dashboard_sort_popular_and_oldest(self):
        older = self.make_published("Older", days_ago=2, saves=5)
        recent = self.make_published("Recent", days_ago=0, saves=1)

        res_popular = self.client.get(self.url, {"sort": "popular"})
        self.assertEqual(res_popular.status_code, 200)
        popular_titles = [p.title for p in res_popular.context["popular_recipes"]]
        self.assertEqual(popular_titles[0], "Older")

        res_oldest = self.client.get(self.url, {"sort": "oldest"})
        self.assertEqual(res_oldest.status_code, 200)
        oldest_titles = [p.title for p in res_oldest.context["popular_recipes"]]
        self.assertEqual(oldest_titles[0], "Older")

    def test_dashboard_sort_popular_uses_likes_and_saves(self):
        liked = self.make_published("Liked", days_ago=1, saves=1)
        saved_only = self.make_published("SavedOnly", days_ago=1, saves=2)

        liker_one = make_user(username="liker_one")
        liker_two = make_user(username="liker_two")
        Like.objects.create(user=liker_one, recipe_post=liked)
        Like.objects.create(user=liker_two, recipe_post=liked)

        res = self.client.get(self.url, {"sort": "popular"})
        self.assertEqual(res.status_code, 200)
        titles = [p.title for p in res.context["popular_recipes"]]
        self.assertEqual(titles[0], "Liked")

    def test_dashboard_for_you_invalid_offset_uses_zero(self):
        make_recipe_post(author=self.user, title="One")
        self.client.login(username=self.user.username, password="Password123")
        response = self.client.get(self.url, {"for_you_ajax": "1", "for_you_offset": "abc"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(payload["count"], 0)

    def test_dashboard_filters_by_ingredient_query(self):
        allowed = make_recipe_post(author=self.user, title="Allowed", prep_time_min=5, cook_time_min=5)
        Ingredient.objects.create(recipe_post=allowed, name="garlic", position=1)
        blocked = make_recipe_post(author=self.user, title="Blocked", prep_time_min=5, cook_time_min=5)
        Ingredient.objects.create(recipe_post=blocked, name="pepper", position=1)
        self.client.login(username=self.user.username, password="Password123")
        response = self.client.get(self.url, {"ingredient": "garlic", "mode": "search"})
        posts = response.context["popular_recipes"]
        self.assertEqual([p.title for p in posts], ["Allowed"])

    def test_dashboard_shopping_scope_ajax(self):
        post = make_recipe_post(author=self.user, title="Shopper")
        Ingredient.objects.create(recipe_post=post, name="Flour", shop_url="https://shop.com/flour", position=1)
        self.client.login(username=self.user.username, password="Password123")
        response = self.client.get(
            self.url,
            {"scope": "shopping", "mode": "search", "ajax": "1"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("html", payload)
        self.assertIn("has_next", payload)

    def test_dashboard_shopping_scope_page_context(self):
        post = make_recipe_post(author=self.user, title="Shopper two")
        Ingredient.objects.create(recipe_post=post, name="Oil", shop_url="https://shop.com/oil", position=1)
        self.client.login(username=self.user.username, password="Password123")
        response = self.client.get(self.url, {"scope": "shopping", "mode": "search"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["shopping_items"])
        self.assertIsInstance(response.context["shopping_page_number"], int)

    def test_dashboard_category_filter(self):
        breakfast = make_recipe_post(author=self.user, title="Breakfast", category="breakfast")
        make_recipe_post(author=self.user, title="Lunch", category="lunch")
        self.client.login(username=self.user.username, password="Password123")
        response = self.client.get(self.url, {"category": "breakfast", "mode": "search"})
        self.assertEqual([p.title for p in response.context["popular_recipes"]], ["Breakfast"])

    def test_dashboard_shopping_scope_filters_query(self):
        post = make_recipe_post(author=self.user, title="Shopper three")
        Ingredient.objects.create(recipe_post=post, name="Olive Oil", shop_url="https://shop.com/oil", position=1)
        Ingredient.objects.create(recipe_post=post, name="Salt", shop_url="https://shop.com/salt", position=2)
        self.client.login(username=self.user.username, password="Password123")
        response = self.client.get(
            self.url,
            {"scope": "shopping", "mode": "search", "q": "olive", "ajax": "1"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("html", payload)

    def test_get_for_you_posts_fallback_when_no_tag_matches(self):
        liked = make_recipe_post(author=self.user, tags=["pasta"])
        Like.objects.create(user=self.user, recipe_post=liked)
        posts = self.feed_service.for_you_posts(self.user, seed=5)
        self.assertIn(liked, posts)

    def test_get_following_posts_returns_empty_when_no_relationships(self):
        posts = self.feed_service.following_posts(self.user)
        self.assertEqual(posts, [])

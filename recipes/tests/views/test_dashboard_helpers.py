from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase
from django.utils import timezone

from recipes.models import Follower, Like, RecipePost
from recipes.tests.test_utils import make_recipe_post, make_user
from recipes.views import dashboard_params, dashboard_utils


class DashboardParamsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _request_with_session(self, params=None):
        request = self.factory.get("/dashboard", params or {})
        from django.contrib.sessions.middleware import SessionMiddleware

        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        request.session.save()
        return request

    def test_parse_dashboard_params_parses_ingredients_and_ajax_header(self):
        request = self.factory.get(
            "/dashboard",
            {
                "have_ingredients": "Garlic, basil\npepper",
                "scope": "shopping",
                "page": "3",
                "category": "dinner",
                "ingredient": "Tomato",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        params = dashboard_params.parse_dashboard_params(request)

        self.assertEqual(params["have_ingredients_raw"], "Garlic, basil\npepper")
        self.assertEqual(params["have_ingredients_list"], ["garlic", "basil", "pepper"])
        self.assertEqual(params["scope"], "shopping")
        self.assertEqual(params["page_number"], 3)
        self.assertTrue(params["is_ajax"])
        self.assertTrue(params["has_search"])
        self.assertEqual(params["ingredient_q"], "Tomato")
        self.assertEqual(params["category"], "dinner")

    def test_parse_dashboard_params_sets_has_search_when_category_filtered(self):
        request = self.factory.get("/dashboard", {"category": "lunch"})

        params = dashboard_params.parse_dashboard_params(request)

        self.assertTrue(params["has_search"])
        self.assertEqual(params["category"], "lunch")
        self.assertEqual(params["mode"], "feed")

    def test_get_for_you_seed_persists_for_ajax_and_resets_for_full_render(self):
        ajax_request = self._request_with_session()
        ajax_request.session["for_you_seed"] = 0.25

        seed = dashboard_params.get_for_you_seed(ajax_request, for_you_ajax=True)

        self.assertEqual(seed, 0.25)
        self.assertEqual(ajax_request.session["for_you_seed"], 0.25)

        full_request = self._request_with_session()
        with patch("recipes.views.dashboard_params.random.random", return_value=0.99):
            seed2 = dashboard_params.get_for_you_seed(full_request, for_you_ajax=False)

        self.assertEqual(seed2, 0.99)
        self.assertEqual(full_request.session["for_you_seed"], 0.99)

    def test_has_search_true_for_search_mode(self):
        request = self.factory.get("/dashboard", {"mode": "search"})
        params = dashboard_params.parse_dashboard_params(request)
        self.assertTrue(params["has_search"])

    def test_is_ajax_detects_query_param(self):
        request = self.factory.get("/dashboard", {"ajax": "1"})
        self.assertTrue(dashboard_params._is_ajax(request))

    def test_normalise_scope_defaults_and_known_values(self):
        self.assertEqual(dashboard_params._normalise_scope("users"), "users")
        self.assertEqual(dashboard_params._normalise_scope("shopping"), "shopping")
        self.assertEqual(dashboard_params._normalise_scope("unknown"), "recipes")
        self.assertEqual(dashboard_params._normalise_scope(None), "recipes")

    def test_safe_int_parses_and_defaults(self):
        self.assertEqual(dashboard_params._safe_int("5", default=3), 5)
        self.assertEqual(dashboard_params._safe_int("-1", default=3), 3)
        self.assertEqual(dashboard_params._safe_int("x", default=2), 2)

    def test_ensure_for_you_seed_sets_session_and_respects_provided_seed(self):
        request = self._request_with_session()
        with patch("recipes.views.dashboard_params.random.random", return_value=0.42):
            seed = dashboard_params._ensure_for_you_seed(request, None)
        self.assertEqual(seed, 0.42)
        self.assertEqual(request.session["for_you_seed"], 0.42)

        seed2 = dashboard_params._ensure_for_you_seed(request, 0.9)
        self.assertEqual(seed2, 0.9)
        self.assertEqual(request.session["for_you_seed"], 0.42)

    def test_parse_have_ingredients_handles_blank(self):
        request = self.factory.get("/dashboard", {"have_ingredients": "   "})
        raw, parsed = dashboard_params._parse_have_ingredients(request)
        self.assertEqual(raw, "")
        self.assertEqual(parsed, [])


class DashboardUtilsTests(TestCase):
    def setUp(self):
        self.user = make_user(username="util_user")
        self.published = lambda title, date: RecipePost.objects.create(
            author=self.user,
            title=title,
            description="d",
            published_at=date,
        )

    def test_normalise_tags_handles_empty_string_and_unknown_type(self):
        self.assertEqual(dashboard_utils._normalise_tags(None), [])
        self.assertEqual(dashboard_utils._normalise_tags("A, b ,"), ["a", "b"])
        self.assertEqual(dashboard_utils._normalise_tags(123), [])
        self.assertEqual(dashboard_utils._normalise_tags(["Pasta ", ""]), ["pasta"])

    def test_apply_query_filters_and_tag_filtering(self):
        liked = make_recipe_post(author=self.user, title="Liked pasta", tags=["pasta"])
        other = make_recipe_post(author=self.user, title="Soup", tags=["soup"])
        Like.objects.create(user=self.user, recipe_post=liked)

        qs = dashboard_utils._apply_query_filters(RecipePost.objects.all(), "pasta")
        self.assertIn(liked, list(qs))
        tagged = dashboard_utils._tag_filtered_qs(qs, ["pasta"], [liked.id])
        self.assertNotIn(liked, list(tagged))
        self.assertNotIn(other, list(tagged))

    def test_tag_filtered_qs_no_preferences_returns_original_queryset(self):
        liked = make_recipe_post(author=self.user, title="Liked pasta", tags=["pasta"])
        other = make_recipe_post(author=self.user, title="Soup", tags=["soup"])

        qs = RecipePost.objects.all()
        # When no preferred tags are provided, the queryset should be returned unchanged,
        # even if liked_post_ids is populated.
        result = dashboard_utils._tag_filtered_qs(qs, [], [liked.id])

        self.assertEqual(set(result.values_list("id", flat=True)), {liked.id, other.id})

    def test_score_and_sort_posts_prefers_recent_tagged(self):
        recent = SimpleNamespace(tags=["pasta"], saved_count=1, published_at=timezone.now())
        old = SimpleNamespace(tags=["pasta"], saved_count=0, published_at=timezone.now() - timedelta(days=15))
        missing_date = SimpleNamespace(tags=["pasta"], saved_count=0, published_at=None)

        scored = dashboard_utils._score_and_sort_posts([old, recent, missing_date], ["pasta"])

        self.assertEqual(scored[0], recent)
        self.assertIn(missing_date, scored)
        score_missing = dashboard_utils._score_post_for_user(missing_date, ["pasta"])
        self.assertGreaterEqual(score_missing, 3)

    def test_score_and_sort_posts_returns_original_when_no_preferences(self):
        posts = [SimpleNamespace(tags=["x"], saved_count=0, published_at=None)]
        self.assertEqual(dashboard_utils._score_and_sort_posts(posts, []), posts)

    def test_get_for_you_posts_uses_seed_limit_and_offset(self):
        posts = [
            make_recipe_post(author=self.user, title=f"P{i}", tags=["x"])
            for i in range(4)
        ]
        result1 = dashboard_utils._get_for_you_posts(self.user, limit=2, offset=1, seed=123)
        result2 = dashboard_utils._get_for_you_posts(self.user, limit=2, offset=1, seed=123)

        self.assertEqual(result1, result2)
        self.assertEqual(len(result1), 2)
        self.assertTrue(all(p in posts for p in result1))

    def test_get_for_you_posts_falls_back_when_tag_filter_empty(self):
        liked = make_recipe_post(author=self.user, title="Liked pasta", tags=["pasta"])
        Like.objects.create(user=self.user, recipe_post=liked)

        posts = dashboard_utils._get_for_you_posts(self.user, limit=None, seed=9)

        self.assertIn(liked, posts)
        self.assertGreaterEqual(len(posts), 1)

    def test_get_following_posts_filters_and_offsets(self):
        author = make_user(username="author")
        Follower.objects.create(follower=self.user, author=author)
        first = make_recipe_post(author=author, title="First dish")
        second = make_recipe_post(author=author, title="Second dish")

        initial = dashboard_utils._get_following_posts(self.user, query="dish", limit=2, offset=0)
        filtered = dashboard_utils._get_following_posts(self.user, query="dish", limit=1, offset=1)

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].id, initial[1].id)

    def test_get_following_posts_returns_empty_when_not_following(self):
        make_recipe_post(author=self.user, title="Solo")

        self.assertEqual(dashboard_utils._get_following_posts(self.user), [])

    def test_search_users_orders_and_handles_blank(self):
        make_user(username="alice")
        make_user(username="bob")
        self.assertEqual(dashboard_utils._search_users(""), [])
        users = dashboard_utils._search_users("a")
        self.assertTrue(any(u.username == "@alice" for u in users))

    def test_search_users_matches_full_name_with_spaces(self):
        target = make_user(username="eileenchamberlain", first_name="Eileen", last_name="Chamberlain")

        results = dashboard_utils._search_users("Eileen Chamberlain")
        self.assertIn(target, results)
        reversed_order = dashboard_utils._search_users("Chamberlain Eileen")
        self.assertIn(target, reversed_order)

    def test_filter_posts_by_prep_time_skips_non_int(self):
        posts = [
            SimpleNamespace(prep_time_min="bad"),
            SimpleNamespace(prep_time_min=5),
            SimpleNamespace(prep_time_min=10),
        ]
        result = dashboard_utils._filter_posts_by_prep_time(posts, min_prep=6, max_prep="11")
        self.assertEqual(result, [posts[2]])

    def test_filter_posts_by_prep_time_handles_invalid_bounds(self):
        posts = [SimpleNamespace(prep_time_min=7)]

        result = dashboard_utils._filter_posts_by_prep_time(posts, min_prep="bad", max_prep=object())

        self.assertEqual(result, posts)

    def test_filter_posts_by_prep_time_applies_max_bound(self):
        posts = [
            SimpleNamespace(prep_time_min=5),
            SimpleNamespace(prep_time_min=15),
        ]

        result = dashboard_utils._filter_posts_by_prep_time(posts, max_prep=10)

        self.assertEqual(result, [posts[0]])

    def test_base_posts_queryset_filters_unpublished_and_orders(self):
        older = self.published("Old", timezone.now() - timedelta(days=1))
        newer = self.published("New", timezone.now())
        RecipePost.objects.create(author=self.user, title="Draft", description="d", published_at=None)

        titles = [p.title for p in dashboard_utils._base_posts_queryset()]

        self.assertNotIn("Draft", titles)
        self.assertEqual(titles[0], "New")
        self.assertEqual(set(titles), {"Old", "New"})

    def test_apply_query_filters_returns_all_when_blank(self):
        make_recipe_post(author=self.user, title="A")
        qs = RecipePost.objects.all()

        result = dashboard_utils._apply_query_filters(qs, "")

        self.assertEqual(set(qs.values_list("id", flat=True)), set(result.values_list("id", flat=True)))

    def test_preferred_tags_for_user_and_anonymous(self):
        anon = AnonymousUser()
        liked_ids, tags = dashboard_utils._preferred_tags_for_user(anon)
        self.assertEqual(liked_ids, [])
        self.assertEqual(tags, [])

        liked_post = make_recipe_post(author=self.user, title="Liked", tags=["One", "one"])
        Like.objects.create(user=self.user, recipe_post=liked_post)

        liked_ids2, tags2 = dashboard_utils._preferred_tags_for_user(self.user)
        self.assertEqual(liked_ids2, [liked_post.id])
        self.assertEqual(tags2, ["one"])

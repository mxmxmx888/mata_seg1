"""Feed and search service used by dashboard views."""
import random
from typing import Iterable, List, Sequence, Tuple

from django.contrib.auth import get_user_model
from django.db.models import (
    Count,
    Exists,
    ExpressionWrapper,
    F,
    IntegerField,
    OuterRef,
    Q,
    QuerySet,
)
from django.utils import timezone

from .privacy import PrivacyService
from recipes.models import RecipePost, Like, Follower, Ingredient
class FeedService:
    """Encapsulate feed ranking, filtering, and user search helpers."""

    def __init__(self, *, privacy_service: PrivacyService | None = None) -> None:
        self.privacy_service = privacy_service or PrivacyService()

    def normalise_tags(self, tags) -> List[str]:
        """Return a lowercased list of tag strings from comma- or list-based input."""
        if not tags:
            return []
        if isinstance(tags, str):
            parts = [p.strip() for p in tags.split(",")]
            return [p.lower() for p in parts if p]
        if isinstance(tags, list):
            return [str(t).strip().lower() for t in tags if str(t).strip()]
        return []

    def user_preference_tags(self, user) -> List[str]:
        """Collect unique tags from posts the user has liked."""
        likes = Like.objects.filter(user=user).select_related("recipe_post")
        tags = (
            tag
            for like in likes
            for tag in self.normalise_tags(getattr(like.recipe_post, "tags", []))
        )
        return list(dict.fromkeys(tags))

    def preferred_tags_for_user(self, user) -> Tuple[List[int], List[str]]:
        """Return (liked_post_ids, preferred_tags) for the user."""
        if not getattr(user, "is_authenticated", False):
            return [], []
        liked_post_ids = list(
            Like.objects.filter(user=user).values_list("recipe_post_id", flat=True)
        )
        preferred_tags = self.user_preference_tags(user) if liked_post_ids else []
        return liked_post_ids, preferred_tags

    def base_posts_queryset(self) -> QuerySet:
        """Base queryset for published recipe posts with related author and images."""
        return (
            RecipePost.objects.filter(published_at__isnull=False)
            .select_related("author")
            .prefetch_related("images")
            .order_by("-published_at", "-created_at")
        )

    def apply_query_filters(self, qs: QuerySet, query: str | None) -> QuerySet:
        """Filter posts by title/description/tags containing the query."""
        if not query:
            return qs
        return qs.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(tags__icontains=query)
        )

    def discover_queryset(
        self,
        user,
        *,
        query: str | None,
        category: str | None,
        ingredient_q: str | None,
        have_ingredients_list: Sequence[str] | None,
        min_prep,
        max_prep,
        sort: str | None,
        privacy: PrivacyService | None = None,
    ) -> QuerySet:
        """Build the discovery queryset with all filters applied."""
        privacy_service = privacy or self.privacy_service
        discover_qs = self._base_discover_queryset(user)
        discover_qs = self.apply_query_filters(discover_qs, query)
        discover_qs = self._apply_category_filter(discover_qs, category)
        discover_qs = self._apply_ingredient_filter(discover_qs, ingredient_q)
        discover_qs = self._apply_time_filters(discover_qs, min_prep, max_prep)
        discover_qs = self._apply_have_ingredients_filter(discover_qs, have_ingredients_list)
        discover_qs = privacy_service.filter_visible_posts(discover_qs, user)
        return self._sort_discover(discover_qs, sort)

    def tag_filtered_qs(
        self, qs: QuerySet, preferred_tags: Sequence[str], liked_post_ids: Sequence[int]
    ) -> QuerySet:
        """Filter posts by preferred tags excluding already liked posts."""
        if not preferred_tags:
            return qs
        tag_filter = Q()
        for tag in preferred_tags:
            tag_filter |= Q(tags__icontains=tag)
        return qs.exclude(id__in=liked_post_ids).filter(tag_filter)

    def score_post_for_user(self, post, preferred_tags: Sequence[str]) -> int:
        """Score a post based on preferred tags, saves, and recency."""
        score = 0
        post_tags = set(self.normalise_tags(getattr(post, "tags", [])))
        pref_set = set(preferred_tags)
        if post_tags & pref_set:
            score += 3
        saved_count = getattr(post, "saved_count", 0) or 0
        score += saved_count
        if getattr(post, "published_at", None):
            age_days = (timezone.now() - post.published_at).days
        else:
            age_days = 999
        score += max(0, 10 - age_days)
        return score

    def score_and_sort_posts(self, posts: Iterable, preferred_tags: Sequence[str]) -> List:
        """Apply scoring and sort posts when preferences exist."""
        if not preferred_tags:
            return list(posts)
        scored = [(self.score_post_for_user(p, preferred_tags), p) for p in posts]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored]

    def for_you_posts(
        self, user, query: str | None = None, limit: int | None = None, offset: int = 0,
        seed=None, privacy: PrivacyService | None = None, sort: str | None = None,
    ) -> List:
        """Return personalised 'for you' posts shuffled by a seed (or sorted when requested)."""
        privacy_service = privacy or self.privacy_service
        base_qs = privacy_service.filter_visible_posts(self.base_posts_queryset(), user)
        base_qs = self.apply_query_filters(base_qs, query)
        liked_post_ids, preferred_tags = self.preferred_tags_for_user(user)
        qs = (
            self.tag_filtered_qs(base_qs, preferred_tags, liked_post_ids)
            if preferred_tags
            else base_qs
        )
        posts = self._for_you_posts_list(qs, base_qs, preferred_tags)
        posts = self.score_and_sort_posts(posts, preferred_tags)
        if sort:
            posts = self._sort_posts(posts, sort)
            return self._slice_posts(posts, limit, offset)
        return self._shuffle_and_slice(posts, seed, limit, offset)

    def following_posts(
        self,
        user,
        query: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> List:
        """Return a list of posts from authors the user follows (optionally limited)."""
        followed_ids = list(
            Follower.objects.filter(follower=user).values_list("author_id", flat=True)
        )
        if not followed_ids:
            return []
        qs = self.base_posts_queryset().filter(author_id__in=followed_ids)
        qs = self.privacy_service.filter_visible_posts(qs, user)
        qs = self.apply_query_filters(qs, query)
        if limit is None:
            return list(qs[offset:])
        return list(qs[offset : offset + limit])

    def search_users(self, query: str | None, limit: int = 18) -> List:
        """Search users by username or name substrings, tolerating spaces."""
        from django.db.models.functions import Concat
        from django.db.models import Value

        User = get_user_model()
        query = (query or "").strip()
        if not query:
            return []
        base_filter = self._user_base_filter(query)
        token_filter = self._token_filter(query)
        if token_filter is not None:
            base_filter |= token_filter
        return list(
            User.objects.annotate(full_name=Concat("first_name", Value(" "), "last_name"))
            .filter(base_filter)
            .order_by("username", "last_name", "first_name")[:limit]
        )

    def filter_posts_by_prep_time(self, posts, min_prep=None, max_prep=None):
        """Filter in-memory posts by prep time bounds; ignores missing/invalid values."""
        min_val = self._safe_int(min_prep)
        max_val = self._safe_int(max_prep)
        if min_val is None and max_val is None:
            return list(posts)
        return [post for post in posts if self._prep_within(post, min_val, max_val)]

    def _for_you_posts_list(self, qs: QuerySet, fallback_qs: QuerySet, preferred_tags: Sequence[str]):
        """Return posts from primary queryset or fallback when preferences yield no results."""
        posts = list(qs)
        if preferred_tags and not posts:
            return list(fallback_qs)
        return posts

    def _shuffle_and_slice(self, posts: List, seed, limit: int | None, offset: int) -> List:
        """Shuffle posts using the provided seed and return a sliced subset."""
        rng = random.Random(seed)
        rng.shuffle(posts)
        if limit is None:
            return posts[offset:]
        return posts[offset : offset + limit]

    def _slice_posts(self, posts: List, limit: int | None, offset: int) -> List:
        """Return a sliced subset without shuffling."""
        if limit is None:
            return posts[offset:]
        return posts[offset : offset + limit]

    def _base_discover_queryset(self, user):
        """Base queryset of published posts, excluding private tags from other authors."""
        return self.base_posts_queryset().exclude(
            Q(tags__icontains="#private") & ~Q(author=user)
        )

    def _apply_category_filter(self, qs, category):
        if category and category != "all":
            return qs.filter(category__iexact=category)
        return qs

    def _apply_ingredient_filter(self, qs, ingredient_q):
        if ingredient_q:
            return qs.filter(ingredients__name__icontains=str(ingredient_q).lower()).distinct()
        return qs

    def _apply_time_filters(self, qs, min_prep, max_prep):
        min_bound = self._safe_int(min_prep)
        max_bound = self._safe_int(max_prep)
        if min_bound is None and max_bound is None:
            return qs

        total_time_expr = ExpressionWrapper(
            F("prep_time_min") + F("cook_time_min"),
            output_field=IntegerField(),
        )
        qs = qs.annotate(total_time_min=total_time_expr)

        if min_bound is not None:
            qs = qs.filter(total_time_min__gte=min_bound)

        if max_bound is not None:
            qs = qs.filter(total_time_min__lte=max_bound)

        return qs

    def _apply_have_ingredients_filter(self, qs, have_ingredients_list):
        if not have_ingredients_list:
            return qs

        allowed_names = [str(name).lower() for name in have_ingredients_list]

        disallowed_subquery = Ingredient.objects.filter(
            recipe_post_id=OuterRef("pk")
        ).exclude(name__in=allowed_names)

        allowed_subquery = Ingredient.objects.filter(
            recipe_post_id=OuterRef("pk"),
            name__in=allowed_names,
        )

        return qs.annotate(
            has_disallowed=Exists(disallowed_subquery),
            has_allowed=Exists(allowed_subquery),
        ).filter(has_disallowed=False, has_allowed=True)

    def _sort_discover(self, discover_qs, sort):
        if sort == "popular":
            return (
                discover_qs.annotate(
                    likes_total=Count("likes", distinct=True),
                    popularity=F("saved_count") + F("likes_total"),
                ).order_by("-popularity", "-published_at", "-created_at")
            )
        if sort == "oldest":
            return discover_qs.order_by("published_at", "created_at")
        return discover_qs.order_by("-published_at", "-created_at")

    def _sort_posts(self, posts: List, sort: str):
        """Sort in-memory posts by popularity or date."""
        if sort == "popular":
            self._refresh_popularity_counts(posts)
            return sorted(posts, key=self._popularity_score, reverse=True)
        reverse = sort != "oldest"
        return sorted(posts, key=self._post_date, reverse=reverse)

    def _refresh_popularity_counts(self, posts: List):
        """Refresh saved/like counts for model instances to avoid stale in-memory values."""
        recipe_posts = [
            post for post in posts if isinstance(post, RecipePost) and getattr(post, "id", None)
        ]
        if not recipe_posts:
            return
        counts = (
            RecipePost.objects.filter(id__in=[p.id for p in recipe_posts])
            .annotate(likes_total=Count("likes", distinct=True))
            .values("id", "saved_count", "likes_total")
        )
        by_id = {row["id"]: row for row in counts}
        for post in recipe_posts:
            data = by_id.get(post.id)
            if not data:
                continue
            post.saved_count = data.get("saved_count", 0)
            post._likes_total = data.get("likes_total", 0)

    def _post_date(self, post):
        return getattr(post, "published_at", None) or getattr(post, "created_at", None) or timezone.datetime.min

    def _popularity_score(self, post):
        saved = getattr(post, "saved_count", 0) or 0
        return saved + self._resolved_likes(post)

    def _resolved_likes(self, post):
        likes = getattr(post, "_likes_total", None)
        if likes is not None:
            return likes or 0

        likes_count = getattr(post, "likes_count", None)
        if likes_count is not None:
            return likes_count or 0

        return self._count_relationship_likes(post)

    def _count_relationship_likes(self, post):
        if not hasattr(post, "likes"):
            return 0
        try:
            return post.likes.count() or 0
        except Exception:
            return 0

    def _user_base_filter(self, query: str):
        """Build a Q filter for user search by username/first name/last name/full name."""
        username_query = query.replace(" ", "")
        return (
            Q(username__icontains=query)
            | Q(username__icontains=username_query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(full_name__icontains=query)
        )

    def _token_filter(self, query: str):
        """Build a Q filter matching all tokens in the query against user fields."""
        tokens = [part for part in query.replace("@", " ").split() if part]
        if not tokens:
            return None
        combined = (
            Q(username__icontains=tokens[0])
            | Q(first_name__icontains=tokens[0])
            | Q(last_name__icontains=tokens[0])
        )
        for token in tokens[1:]:
            combined &= (
                Q(username__icontains=token)
                | Q(first_name__icontains=token)
                | Q(last_name__icontains=token)
            )
        return combined

    def _safe_int(self, value):
        """Safely convert a value to int, returning None on failure."""
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _prep_within(self, post, min_val, max_val):
        """Check if a post's prep time falls within the specified bounds."""
        try:
            prep = int(getattr(post, "prep_time_min", None))
        except (TypeError, ValueError):
            return False
        if min_val is not None and prep < min_val:
            return False
        if max_val is not None and prep > max_val:
            return False
        return True

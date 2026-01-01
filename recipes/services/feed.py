"""Feed and search service used by dashboard views."""

import random
from typing import Iterable, List, Sequence, Tuple

from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet
from django.utils import timezone

from .privacy import PrivacyService
from recipes.models import RecipePost, Like, Follower


class FeedService:
    """Encapsulate feed ranking, filtering, and user search helpers."""

    def __init__(self, *, privacy_service: PrivacyService | None = None) -> None:
        self.privacy_service = privacy_service or PrivacyService()

    # --- tag helpers -----------------------------------------------------
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
        tags: List[str] = []
        like_qs = Like.objects.filter(user=user).select_related("recipe_post")
        for like in like_qs:
            tags.extend(self.normalise_tags(getattr(like.recipe_post, "tags", [])))
        seen = set()
        result = []
        for t in tags:
            if t not in seen:
                seen.add(t)
                result.append(t)
        return result

    def preferred_tags_for_user(self, user) -> Tuple[List[int], List[str]]:
        """Return (liked_post_ids, preferred_tags) for the user."""
        if not getattr(user, "is_authenticated", False):
            return [], []
        liked_post_ids = list(
            Like.objects.filter(user=user).values_list("recipe_post_id", flat=True)
        )
        preferred_tags = self.user_preference_tags(user) if liked_post_ids else []
        return liked_post_ids, preferred_tags

    # --- query building --------------------------------------------------
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

    # --- scoring and sorting --------------------------------------------
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

    # --- feed construction ----------------------------------------------
    def for_you_posts(
        self,
        user,
        query: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        seed=None,
        privacy: PrivacyService | None = None,
    ) -> List:
        """Return personalised 'for you' posts shuffled by a seed."""
        privacy_service = privacy or self.privacy_service
        base_qs = privacy_service.filter_visible_posts(self.base_posts_queryset(), user)
        liked_post_ids, preferred_tags = self.preferred_tags_for_user(user)
        qs = self.apply_query_filters(base_qs, query)
        base_qs = self.apply_query_filters(base_qs, query)
        if preferred_tags:
            qs = self.tag_filtered_qs(qs, preferred_tags, liked_post_ids)
        posts = self._for_you_posts_list(qs, base_qs, preferred_tags)
        posts = self.score_and_sort_posts(posts, preferred_tags)
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
        if query:
            qs = qs.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(tags__icontains=query)
            )
        if limit is None:
            return list(qs[offset:])
        return list(qs[offset : offset + limit])

    # --- search ---------------------------------------------------------
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

    # --- in-memory filters ----------------------------------------------
    def filter_posts_by_prep_time(self, posts, min_prep=None, max_prep=None):
        """
        Filter in-memory posts by prep time bounds.
        Values that cannot be coerced to ints or missing prep times are ignored.
        """
        min_val = self._safe_int(min_prep)
        max_val = self._safe_int(max_prep)
        if min_val is None and max_val is None:
            return list(posts)
        return [post for post in posts if self._prep_within(post, min_val, max_val)]

    # --- internal helpers -----------------------------------------------
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

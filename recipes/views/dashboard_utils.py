import random
from django.contrib.auth import get_user_model
from django.db.models import Q, Exists, OuterRef
from django.utils import timezone
from recipes.services import PrivacyService

try:
    from recipes.models import RecipePost, Like, Follower, Ingredient
except Exception:
    from recipes.models.recipe_post import RecipePost
    from recipes.models.like import Like
    from recipes.models.followers import Follower
    from recipes.models.ingredient import Ingredient

privacy_service = PrivacyService()

def _normalise_tags(tags):
    """Return a lowercased list of tag strings from comma- or list-based input."""
    if not tags:
        return []
    if isinstance(tags, str):
        parts = [p.strip() for p in tags.split(",")]
        return [p.lower() for p in parts if p]
    if isinstance(tags, list):
        return [str(t).strip().lower() for t in tags if str(t).strip()]
    return []

def _user_preference_tags(user):
    """Collect unique tags from posts the user has liked."""
    tags = []

    like_qs = Like.objects.filter(user=user).select_related("recipe_post")

    for like in like_qs:
        tags.extend(_normalise_tags(getattr(like.recipe_post, "tags", [])))

    seen = set()
    result = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result

def _base_posts_queryset():
    """Base queryset for published recipe posts with related author and images."""
    return (
        RecipePost.objects.filter(published_at__isnull=False)
        .select_related("author")
        .prefetch_related("images")
        .order_by("-published_at", "-created_at")
    )

def _score_post_for_user(post, preferred_tags):
    """Score a post based on preferred tags, saves, and recency."""
    score = 0

    post_tags = set(_normalise_tags(getattr(post, "tags", [])))
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

def _preferred_tags_for_user(user):
    """Return (liked_post_ids, preferred_tags) for the user."""
    if not getattr(user, "is_authenticated", False):
        return [], []
    liked_post_ids = list(
        Like.objects.filter(user=user).values_list("recipe_post_id", flat=True)
    )
    preferred_tags = _user_preference_tags(user) if liked_post_ids else []
    return liked_post_ids, preferred_tags


def _apply_query_filters(qs, query):
    """Filter posts by title/description/tags containing the query."""
    if not query:
        return qs
    return qs.filter(
        Q(title__icontains=query)
        | Q(description__icontains=query)
        | Q(tags__icontains=query)
    )


def _tag_filtered_qs(qs, preferred_tags, liked_post_ids):
    """Filter posts by preferred tags excluding already liked posts."""
    if not preferred_tags:
        return qs
    tag_filter = Q()
    for tag in preferred_tags:
        tag_filter |= Q(tags__icontains=tag)
    return qs.exclude(id__in=liked_post_ids).filter(tag_filter)


def _score_and_sort_posts(posts, preferred_tags):
    """Apply scoring and sort posts when preferences exist."""
    if not preferred_tags:
        return posts
    scored = [(_score_post_for_user(p, preferred_tags), p) for p in posts]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored]


def _get_for_you_posts(user, query=None, limit=None, offset=0, seed=None, privacy=privacy_service):
    """Return personalised 'for you' posts shuffled by a seed."""
    base_qs = privacy.filter_visible_posts(_base_posts_queryset(), user)
    qs = base_qs

    liked_post_ids, preferred_tags = _preferred_tags_for_user(user)

    qs = _apply_query_filters(qs, query)
    base_qs = _apply_query_filters(base_qs, query)

    if preferred_tags:
        qs = _tag_filtered_qs(qs, preferred_tags, liked_post_ids)

    posts = list(qs)
    if preferred_tags and not posts:
        # Fallback to general feed if tag-based filtering produced nothing
        posts = list(base_qs)

    posts = _score_and_sort_posts(posts, preferred_tags)

    rng = random.Random(seed)
    rng.shuffle(posts)

    if limit is None:
        return posts[offset:]
    return posts[offset:offset + limit]

def _get_following_posts(user, query=None, limit=12, offset=0):
    """Return a list of posts from authors the user follows."""
    followed_ids = list(
        Follower.objects.filter(follower=user).values_list("author_id", flat=True)
    )
    if not followed_ids:
        return []

    qs = _base_posts_queryset().filter(author_id__in=followed_ids)
    qs = privacy_service.filter_visible_posts(qs, user)

    if query:
        qs = qs.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(tags__icontains=query)
        )

    return list(qs[offset:offset + limit])

def _search_users(query, limit=18):
    """Search users by username substring."""
    User = get_user_model()
    if not query:
        return []
    return list(
        User.objects.filter(username__icontains=query)
        .order_by("username")[:limit]
    )

def _filter_posts_by_prep_time(posts, min_prep=None, max_prep=None):
    """
    Filter in-memory posts by prep time bounds.
    Values that cannot be coerced to ints or missing prep times are ignored.
    """
    try:
        min_val = int(min_prep) if min_prep is not None else None
    except (TypeError, ValueError):
        min_val = None

    try:
        max_val = int(max_prep) if max_prep is not None else None
    except (TypeError, ValueError):
        max_val = None

    if min_val is None and max_val is None:
        return list(posts)

    filtered = []
    for post in posts:
        try:
            prep = int(getattr(post, "prep_time_min", None))
        except (TypeError, ValueError):
            continue

        if min_val is not None and prep < min_val:
            continue
        if max_val is not None and prep > max_val:
            continue
        filtered.append(post)
    return filtered

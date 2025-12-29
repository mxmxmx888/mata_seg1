"""Helpers for assembling profile and collection metadata."""

from recipes.models import Favourite
from recipes.models.favourite_item import FavouriteItem

def _post_image_url(post):
    """Return the best image URL for a post if available."""
    return getattr(post, "primary_image_url", None) or getattr(post, "image", None)

def profile_data_for_user(user):
    """Return profile metadata dict for display components."""
    fallback_handle = "@anmzn"
    handle = user.username or fallback_handle
    display_name = user.get_full_name() or user.username or "cook"
    bio = getattr(user, "bio", "") or ""
    return {
        "display_name": display_name,
        "handle": handle,
        "tagline": bio,
        "following": 2,
        "followers": 0,
        "avatar_url": user.avatar_url,
        "is_private": getattr(user, "is_private", False),
    }


def _collection_meta(items, favourite):
    """Compute last_saved_at, cover image url, and item count for a favourite."""

    last_saved_at = favourite.created_at
    cover_post = favourite.cover_post if _post_image_url(getattr(favourite, "cover_post", None)) else None
    first_image_post = None
    visible_posts = []

    for item in items:
        post = item.recipe_post
        if not post:
            continue
        visible_posts.append(post)
        if item.added_at and (last_saved_at is None or item.added_at > last_saved_at):
            last_saved_at = item.added_at
        if not first_image_post and _post_image_url(post):
            first_image_post = post

    cover_post = cover_post or first_image_post
    cover_url = _post_image_url(cover_post) if cover_post else None
    return last_saved_at, cover_url, len(visible_posts)


def collections_for_user(user):
    """
    Build collection cards for the given user from Favourite/FavouriteItem.
    Each Favourite becomes a collection backed by the user's saved posts.
    """
    favourites = Favourite.objects.filter(user=user).prefetch_related("items__recipe_post")
    collections = [_collection_card(fav) for fav in favourites]
    collections.sort(key=lambda c: c.get("last_saved_at"), reverse=True)
    return collections

def _collection_card(fav):
    items = list(fav.items.select_related("recipe_post").order_by("-added_at", "-id"))
    last_saved_at, cover_url, count = _collection_meta(items, fav)
    return {
        "id": str(fav.id),
        "slug": str(fav.id),
        "title": fav.name,
        "count": count,
        "privacy": None,
        "cover": cover_url,
        "has_image": bool(cover_url),
        "last_saved_at": last_saved_at,
    }

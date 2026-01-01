"""Helper utilities used by recipe view functions and templates."""

from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

from recipes.forms.comment_form import CommentForm
from recipes.services.recipe_posts import RecipePostService
_recipe_service = RecipePostService()


def is_hx(request):
    """Return True when the request was made via HTMX/XMLHttpRequest."""
    return request.headers.get("HX-Request") or request.headers.get("x-requested-with") == "XMLHttpRequest"


def set_primary_image(recipe):
    """Persist the first RecipeImage URL onto the legacy image field for display."""
    _recipe_service.set_primary_image(recipe)


def _primary_image_url(recipe):
    """Return best primary image URL (first gallery image fallback to legacy)."""
    first = recipe.images.first()
    if not first:
        return recipe.image or None
    try:
        return first.image.url
    except ValueError:
        return recipe.image or None


def _gallery_images(images_qs):
    """Return URLs for gallery images beyond the first."""
    gallery = []
    for extra in images_qs[1:]:
        url = _safe_image_url(extra)
        if url:
            gallery.append(url)
    return gallery


def _safe_image_url(image_obj):
    try:
        return image_obj.image.url
    except ValueError:
        return None


def collection_thumb(cover_post, fallback_post):
    """Choose a thumbnail URL for a collection using cover or fallback posts."""
    return _recipe_service.collection_thumb(cover_post, fallback_post)


def primary_image_url(recipe):
    """Return the best primary image URL for a recipe."""
    return _primary_image_url(recipe)


def gallery_images(images_qs):
    """Return gallery image URLs beyond the primary image."""
    return _gallery_images(images_qs)


def collections_modal_state(user, recipe):
    """Build modal-friendly collection metadata for a user and target recipe."""
    return _recipe_service.collections_modal_state(user, recipe)

def _favourites_for(user):
    """Return all Favourite collections for a user with prefetched items and cover posts."""
    return _recipe_service._favourites_for(user)

def _collection_entry(fav, recipe):
    """Build a dictionary entry representing a collection's state relative to a recipe."""
    return _recipe_service._collection_entry(fav, recipe)

def _first_item_post(items):
    """Return the first recipe post found in a list of FavouriteItems, or None."""
    return _recipe_service._first_item_post(items)

def _last_saved_at(items, default):
    """Find the most recent added_at timestamp from items, or return default."""
    return _recipe_service._last_saved_at(items, default)

def user_reactions(request_user, recipe):
    """Return flags and counts for likes/saves and following for the current user."""
    return _recipe_service.user_reactions(request_user, recipe)


def recipe_media(recipe):
    """Return primary image and gallery images for a recipe."""
    images_qs = recipe.images.all()
    image_url = _primary_image_url(recipe)
    gallery_images = _gallery_images(images_qs) if images_qs.count() > 1 else []
    return image_url, gallery_images


def recipe_metadata(recipe):
    """Return display metadata for the recipe/post."""
    author_handle = getattr(recipe.author, "username", "")
    total_time = (recipe.prep_time_min or 0) + (recipe.cook_time_min or 0)
    cook_time = f"{total_time} min" if total_time else "N/A"
    serves = getattr(recipe, "serves", 0) or 0
    summary = recipe.description or ""
    tags_list = recipe.tags or []
    post_date = (recipe.published_at or recipe.created_at or timezone.now()).strftime("%b %d, %Y")
    source_link = reverse("recipe_detail", args=[recipe.id])
    source_label = "Recipi"
    return {
        "author_handle": author_handle,
        "cook_time": cook_time,
        "serves": serves,
        "summary": summary,
        "tags_list": tags_list,
        "post_date": post_date,
        "source_link": source_link,
        "source_label": source_label,
    }


def ingredient_lists(recipe):
    """Split ingredients into non-shop list and shop-linked list."""
    return _recipe_service.ingredient_lists(recipe)


def recipe_steps(recipe):
    """Return ordered step descriptions for a recipe."""
    return _recipe_service.recipe_steps(recipe)


def build_recipe_context(recipe, request_user, comments):
    """Assemble the context dict for recipe_detail."""
    return _merge_recipe_context(
        recipe,
        comments,
        collections_modal_state(request_user, recipe),
        user_reactions(request_user, recipe),
        recipe_media(recipe),
        recipe_metadata(recipe),
        ingredient_lists(recipe),
        recipe_steps(recipe),
    )

def _merge_recipe_context(recipe, comments, collections_for_modal, reactions, media, meta, ingredients_data, steps):
    """Merge all recipe detail components into a single context dictionary."""
    image_url, gallery_images = media
    ingredients, shop_ingredients = ingredients_data
    return {
        **{
            "recipe": recipe,
            "post": recipe,
            "image_url": image_url,
            "gallery_images": gallery_images,
            "ingredients": ingredients,
            "shop_ingredients": shop_ingredients,
            "steps": steps,
            "comments": comments,
            "comment_form": CommentForm(),
            "save_collections": collections_for_modal,
            "visibility": recipe.visibility,
            "video_url": None,
            "view_similar": [],
        },
        **_meta_context(recipe, meta),
        **_reaction_context(reactions),
    }

def _meta_context(recipe, meta):
    """Extract metadata fields into a flat dictionary for template context."""
    return {
        "author_handle": meta["author_handle"],
        "title": recipe.title,
        "cook_time": meta["cook_time"],
        "serves": meta["serves"],
        "summary": meta["summary"],
        "tags": meta["tags_list"],
        "post_date": meta["post_date"],
        "source_link": meta["source_link"],
        "source_label": meta["source_label"],
    }

def _reaction_context(reactions):
    """Extract reaction fields into a flat dictionary for template context."""
    return {
        "user_liked": reactions["user_liked"],
        "user_saved": reactions["user_saved"],
        "is_following_author": reactions["is_following_author"],
        "likes_count": reactions["likes_count"],
        "saves_count": reactions["saves_count"],
    }


def resolve_collection(request, recipe):
    """Determine the Favourite collection to toggle, creating if needed."""
    collection_id = request.POST.get("collection_id") or request.GET.get("collection_id")
    collection_name = request.POST.get("collection_name") or request.GET.get("collection_name")
    return _recipe_service.resolve_collection(
        request.user,
        collection_id=collection_id,
        collection_name=collection_name,
    )


def toggle_save(favourite, recipe):
    """Toggle save state for a recipe within a Favourite; return (is_saved_now, new_count)."""
    return _recipe_service.toggle_save(favourite, recipe)


def hx_response_or_redirect(request, target_url):
    """Return 204 for HX requests or redirect for normal requests."""
    if is_hx(request):
        return HttpResponse(status=204)
    return redirect(target_url)

"""Helper utilities used by recipe view functions and templates."""

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone

from recipes.forms.comment_form import CommentForm
from recipes.models import Favourite
from recipes.models.favourite_item import FavouriteItem
from recipes.models.ingredient import Ingredient
from recipes.models.like import Like
from recipes.models.recipe_post import RecipePost
from recipes.models.recipe_step import RecipeStep
from recipes.models.followers import Follower


def is_hx(request):
    """Return True when the request was made via HTMX/XMLHttpRequest."""
    return request.headers.get("HX-Request") or request.headers.get("x-requested-with") == "XMLHttpRequest"


def set_primary_image(recipe):
    """Persist the first RecipeImage URL onto the legacy image field for display."""
    primary_image = recipe.images.first()
    if primary_image and primary_image.image:
        recipe.image = primary_image.image.url
        recipe.save(update_fields=["image"])


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
    thumb_url = getattr(cover_post, "primary_image_url", None) or getattr(cover_post, "image", None)
    if not thumb_url and fallback_post:
        thumb_url = getattr(fallback_post, "primary_image_url", None) or getattr(fallback_post, "image", None)
    return thumb_url or "https://placehold.co/1200x800/0f0f14/ffffff?text=Collection"


def primary_image_url(recipe):
    """Return the best primary image URL for a recipe."""
    return _primary_image_url(recipe)


def gallery_images(images_qs):
    """Return gallery image URLs beyond the primary image."""
    return _gallery_images(images_qs)


def collections_modal_state(user, recipe):
    """Build modal-friendly collection metadata for a user and target recipe."""
    collections = [_collection_entry(fav, recipe) for fav in _favourites_for(user)]
    collections.sort(key=lambda c: c.get("last_saved_at") or c.get("created_at"), reverse=True)
    collections.sort(key=lambda c: 0 if c.get("saved") else 1)
    return collections

def _favourites_for(user):
    return Favourite.objects.filter(user=user).prefetch_related("items__recipe_post", "cover_post")

def _collection_entry(fav, recipe):
    items = list(fav.items.all())
    saved_here = any(item.recipe_post_id == recipe.id for item in items)
    cover_post = fav.cover_post or _first_item_post(items)
    fallback_cover = recipe if saved_here else _first_item_post(items)
    return {
        "id": str(fav.id),
        "name": fav.name,
        "saved": saved_here,
        "count": len(items),
        "thumb_url": collection_thumb(cover_post, fallback_cover),
        "last_saved_at": _last_saved_at(items, fav.created_at),
        "created_at": fav.created_at,
    }

def _first_item_post(items):
    for item in items:
        if item.recipe_post:
            return item.recipe_post
    return None

def _last_saved_at(items, default):
    latest = default
    for item in items:
        if item.added_at and (latest is None or item.added_at > latest):
            latest = item.added_at
    return latest

def user_reactions(request_user, recipe):
    """Return flags and counts for likes/saves and following for the current user."""
    user_liked = Like.objects.filter(user=request_user, recipe_post=recipe).exists()
    user_saved = FavouriteItem.objects.filter(
        favourite__user=request_user,
        recipe_post=recipe,
    ).exists()
    is_following_author = Follower.objects.filter(
        follower=request_user,
        author=recipe.author,
    ).exists()
    likes_count = Like.objects.filter(recipe_post=recipe).count()
    saves_count = FavouriteItem.objects.filter(recipe_post=recipe).count()
    return {
        "user_liked": user_liked,
        "user_saved": user_saved,
        "is_following_author": is_following_author,
        "likes_count": likes_count,
        "saves_count": saves_count,
    }


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
    ingredients_all = list(Ingredient.objects.filter(recipe_post=recipe).order_by("position"))
    shop_ingredients = [
        ing for ing in ingredients_all if getattr(ing, "shop_url", None) and ing.shop_url.strip()
    ]
    non_shop_ingredients = [ing for ing in ingredients_all if ing not in shop_ingredients]
    return non_shop_ingredients, shop_ingredients


def recipe_steps(recipe):
    """Return ordered step descriptions for a recipe."""
    steps_qs = RecipeStep.objects.filter(recipe_post=recipe).order_by("position")
    return [s.description for s in steps_qs]


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

    if collection_id:
        favourite = get_object_or_404(Favourite, id=collection_id, user=request.user)
        created_collection = False
    else:
        name = (collection_name or "favourites").strip() or "favourites"
        favourite, created_collection = Favourite.objects.get_or_create(
            user=request.user,
            name=name,
        )
    return favourite, created_collection


def toggle_save(favourite, recipe):
    """Toggle save state for a recipe within a Favourite; return (is_saved_now, new_count)."""
    existing = FavouriteItem.objects.filter(
        favourite=favourite,
        recipe_post=recipe,
    )

    if existing.exists():
        existing.delete()
        new_count = max(0, (recipe.saved_count or 0) - 1)
        return False, new_count

    FavouriteItem.objects.create(
        favourite=favourite,
        recipe_post=recipe,
    )
    new_count = (recipe.saved_count or 0) + 1
    return True, new_count


def hx_response_or_redirect(request, target_url):
    """Return 204 for HX requests or redirect for normal requests."""
    if is_hx(request):
        return HttpResponse(status=204)
    return redirect(target_url)

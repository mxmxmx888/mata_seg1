from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from recipes.forms.recipe_forms import RecipePostForm
from recipes.forms.comment_form import CommentForm
from recipes.services import PrivacyService
from recipes.services import FollowService

try:
    from recipes.models import RecipePost, Ingredient, RecipeStep, Favourite, Like, Comment
    from recipes.models.favourite_item import FavouriteItem
except Exception:  # pragma: no cover - fallback imports for alternate module paths
    from recipes.models.recipe_post import RecipePost
    from recipes.models.ingredient import Ingredient
    from recipes.models.recipe_step import RecipeStep
    from mata_seg1.recipes.models.collection import Favourite
    from recipes.models.like import Like
    from recipes.models.comment import Comment
try:
    from recipes.models.followers import Follower
except Exception:  # pragma: no cover - fallback imports for alternate module paths
    from recipes.models import Follower

User = get_user_model()
privacy_service = PrivacyService()
follow_service_factory = FollowService

def _is_hx(request):
    return request.headers.get("HX-Request") or request.headers.get("x-requested-with") == "XMLHttpRequest"


def _set_primary_image(recipe):
    primary_image = recipe.images.first()
    if primary_image and primary_image.image:
        recipe.image = primary_image.image.url
        recipe.save(update_fields=["image"])


def _primary_image_url(recipe):
    first = recipe.images.first()
    if not first:
        return recipe.image or None
    try:
        return first.image.url
    except ValueError:
        return recipe.image or None


def _gallery_images(images_qs):
    gallery = []
    for extra in images_qs[1:]:
        try:
            gallery.append(extra.image.url)
        except ValueError:
            continue
    return gallery


def _collection_thumb(cover_post, fallback_post):
    thumb_url = getattr(cover_post, "primary_image_url", None) or getattr(cover_post, "image", None)
    if not thumb_url and fallback_post:
        thumb_url = getattr(fallback_post, "primary_image_url", None) or getattr(fallback_post, "image", None)
    return thumb_url or "https://placehold.co/1200x800/0f0f14/ffffff?text=Collection"


def _collections_modal_state(user, recipe):
    collections = []
    favourites_qs = Favourite.objects.filter(user=user).prefetch_related("items__recipe_post", "cover_post")
    for fav in favourites_qs:
        items = list(fav.items.all())
        is_in_collection = any(item.recipe_post_id == recipe.id for item in items)
        last_saved_at = fav.created_at
        cover_post = fav.cover_post
        fallback_cover = recipe if is_in_collection else None

        for item in items:
            if item.added_at and (last_saved_at is None or item.added_at > last_saved_at):
                last_saved_at = item.added_at
            if not cover_post and item.recipe_post:
                cover_post = item.recipe_post
            if not fallback_cover and item.recipe_post:
                fallback_cover = item.recipe_post

        thumb_url = _collection_thumb(cover_post, fallback_cover)

        collections.append(
            {
                "id": str(fav.id),
                "name": fav.name,
                "saved": is_in_collection,
                "count": len(items),
                "thumb_url": thumb_url,
                "last_saved_at": last_saved_at,
            }
        )

    collections.sort(key=lambda c: c.get("last_saved_at") or c.get("created_at"), reverse=True)
    collections.sort(key=lambda c: 0 if c.get("saved") else 1)
    return collections


def _user_reactions(request_user, recipe):
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


def _recipe_media(recipe):
    """Return primary image and gallery images for a recipe."""
    images_qs = recipe.images.all()
    image_url = _primary_image_url(recipe)
    gallery_images = _gallery_images(images_qs) if images_qs.count() > 1 else []
    return image_url, gallery_images


def _recipe_metadata(recipe):
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


def _ingredient_lists(recipe):
    """Split ingredients into all vs shop-linked sets."""
    ingredients_all = list(Ingredient.objects.filter(recipe_post=recipe).order_by("position"))
    shop_ingredients = [
        ing for ing in ingredients_all if getattr(ing, "shop_url", None) and ing.shop_url.strip()
    ]
    return ingredients_all, shop_ingredients


def _recipe_steps(recipe):
    """Return ordered step descriptions for a recipe."""
    steps_qs = RecipeStep.objects.filter(recipe_post=recipe).order_by("position")
    return [s.description for s in steps_qs]


def _build_recipe_context(recipe, request_user, comments):
    """Assemble the context dict for recipe_detail."""
    collections_for_modal = _collections_modal_state(request_user, recipe)
    reactions = _user_reactions(request_user, recipe)
    image_url, gallery_images = _recipe_media(recipe)
    meta = _recipe_metadata(recipe)
    ingredients, shop_ingredients = _ingredient_lists(recipe)
    steps = _recipe_steps(recipe)

    return {
        "recipe": recipe,
        "post": recipe,
        "image_url": image_url,
        "author_handle": meta["author_handle"],
        "title": recipe.title,
        "cook_time": meta["cook_time"],
        "serves": meta["serves"],
        "ingredients": ingredients,
        "shop_ingredients": shop_ingredients,
        "steps": steps,
        "summary": meta["summary"],
        "tags": meta["tags_list"],
        "post_date": meta["post_date"],
        "source_link": meta["source_link"],
        "source_label": meta["source_label"],
        "user_liked": reactions["user_liked"],
        "user_saved": reactions["user_saved"],
        "is_following_author": reactions["is_following_author"],
        "likes_count": reactions["likes_count"],
        "saves_count": reactions["saves_count"],
        "comments": comments,
        "comment_form": CommentForm(),
        "gallery_images": gallery_images,
        "video_url": None,
        "view_similar": [],
        "save_collections": collections_for_modal,
        "visibility": recipe.visibility,
    }


def _resolve_collection(request, recipe):
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


def _toggle_save(favourite, recipe):
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


@login_required
def recipe_create(request):
    form = RecipePostForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        cleaned = form.cleaned_data
        tags_list = form.parse_tags()
        recipe = RecipePost.objects.create(
            author=request.user,
            title=cleaned["title"],
            description=cleaned.get("description") or "",
            prep_time_min=cleaned.get("prep_time_min") or 0,
            cook_time_min=cleaned.get("cook_time_min") or 0,
            serves=cleaned.get("serves") or 0,
            nutrition=cleaned.get("nutrition") or "",
            tags=tags_list,
            category=cleaned.get("category") or "",
            visibility=cleaned.get("visibility") or RecipePost.VISIBILITY_PUBLIC,
            published_at=timezone.now(),
        )
        form.create_ingredients(recipe)
        form.create_steps(recipe)
        form.create_images(recipe)
        _set_primary_image(recipe)
        return redirect("recipe_detail", post_id=recipe.id)

    return render(
        request,
        "app/create_recipe.html",
        {
            "form": form,
            "exclude_fields": ["shop_images"],  # render form fields except shopping images (handled manually)
        },
    )

@login_required
def recipe_edit(request, post_id):
    recipe = get_object_or_404(RecipePost, id=post_id, author=request.user)
    form = RecipePostForm(request.POST or None, request.FILES or None, instance=recipe)
    if request.method == "POST" and form.is_valid():
        cleaned = form.cleaned_data
        tags_list = form.parse_tags()
        recipe.title = cleaned["title"]
        recipe.description = cleaned.get("description") or ""
        recipe.prep_time_min = cleaned.get("prep_time_min") or 0
        recipe.cook_time_min = cleaned.get("cook_time_min") or 0
        recipe.serves = cleaned.get("serves") or 0
        recipe.nutrition = cleaned.get("nutrition") or ""
        recipe.tags = tags_list
        recipe.category = cleaned.get("category") or ""
        recipe.visibility = cleaned.get("visibility") or RecipePost.VISIBILITY_PUBLIC
        recipe.save()
        form.create_ingredients(recipe)
        form.create_steps(recipe)
        form.create_images(recipe)
        _set_primary_image(recipe)
        messages.success(request, "Recipe updated.")
        return redirect("recipe_detail", post_id=recipe.id)

    return render(
        request,
        "app/edit_recipe.html",
        {
            "form": form,
            "recipe": recipe,
            # render form fields except images (kept as-is on edit) and shopping images (handled manually)
            "exclude_fields": ["images", "shop_images"],
        },
    )

@login_required
def recipe_detail(request, post_id):
    recipe = get_object_or_404(RecipePost, id=post_id)

    if not privacy_service.can_view_post(request.user, recipe):
        raise Http404("Post not available.")

    comments = recipe.comments.select_related("user").order_by("-created_at")
    context = _build_recipe_context(recipe, request.user, comments)
    # Ensure source_link is absolute for sharing
    context["source_link"] = request.build_absolute_uri(context["source_link"])
    return render(request, "post/post_detail.html", context)

@login_required
def saved_recipes(request):
    favourite_items = (
        FavouriteItem.objects.filter(favourite__user=request.user)
        .select_related("recipe_post")
        .order_by("-added_at")
    )

    seen_ids = set()
    posts = []
    for item in favourite_items:
        post = item.recipe_post
        if not post or post.id in seen_ids:
            continue
        seen_ids.add(post.id)
        posts.append(post)

    return render(request, "app/saved_recipes.html", {"posts": posts})

@login_required
def delete_my_recipe(request, post_id):
    recipe = get_object_or_404(RecipePost, id=post_id, author=request.user)

    if request.method == "POST":
        recipe.delete()
        messages.success(request, "Recipe deleted.")
        return redirect("profile")

    return redirect("recipe_detail", post_id=recipe.id)

@login_required
def toggle_favourite(request, post_id):
    recipe = get_object_or_404(RecipePost, id=post_id)
    favourite, created_collection = _resolve_collection(request, recipe)
    is_saved_now, new_count = _toggle_save(favourite, recipe)
    RecipePost.objects.filter(id=recipe.id).update(saved_count=new_count)

    if _is_hx(request):
        return JsonResponse(
            {
                "saved": is_saved_now,
                "saved_count": new_count,
                "collection": {
                    "id": str(favourite.id),
                    "name": favourite.name,
                    "created": created_collection,
                    "thumb_url": _collection_thumb(favourite.cover_post, recipe),
                },
            }
        )

    return redirect(request.META.get("HTTP_REFERER") or reverse("recipe_detail", args=[recipe.id]))

@login_required
def toggle_like(request, post_id):
    recipe = get_object_or_404(RecipePost, id=post_id)
    existing = Like.objects.filter(user=request.user, recipe_post=recipe)

    if existing.exists():
        existing.delete()
    else:
        Like.objects.create(user=request.user, recipe_post=recipe)

    if _is_hx(request):
        return HttpResponse(status=204)

    return redirect(request.META.get("HTTP_REFERER") or reverse("recipe_detail", args=[recipe.id]))

@login_required
def toggle_follow(request, username):
    target_user = get_object_or_404(User, username=username)

    if target_user == request.user:
        if request.headers.get("HX-Request") or request.headers.get("x-requested-with") == "XMLHttpRequest":
            return HttpResponse(status=204)
        return redirect(request.META.get("HTTP_REFERER") or reverse("dashboard"))

    service = follow_service_factory(request.user)
    result = service.toggle_follow(target_user)

    if _is_hx(request):
        return HttpResponse(status=204)

    return redirect(request.META.get("HTTP_REFERER") or reverse("dashboard"))

@login_required
def add_comment(request, post_id):
    recipe = get_object_or_404(RecipePost, id=post_id)
    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.recipe_post = recipe
            comment.user = request.user
            comment.save()
            messages.success(request, "Comment posted.")
        else:
            messages.error(request, "Error posting comment.")
    
    return redirect("recipe_detail", post_id=recipe.id)

@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if comment.user != request.user:
        messages.error(request, "You are not allowed to delete this comment.")
        return redirect('recipe_detail', post_id=comment.recipe_post.id)
    post_id = comment.recipe_post.id
    comment.delete()
    messages.success(request, "Comment deleted.")
    return redirect('recipe_detail', post_id=post_id)

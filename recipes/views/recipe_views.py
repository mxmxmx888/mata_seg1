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


def _collections_modal_state(user, recipe):
    collections = []
    favourites_qs = Favourite.objects.filter(user=user).prefetch_related("items__recipe_post", "cover_post")
    for fav in favourites_qs:
        items = list(fav.items.all())
        is_in_collection = any(item.recipe_post_id == recipe.id for item in items)
        last_saved_at = fav.created_at
        cover_post = fav.cover_post

        for item in items:
            if item.added_at and (last_saved_at is None or item.added_at > last_saved_at):
                last_saved_at = item.added_at
            if not cover_post and item.recipe_post:
                cover_post = item.recipe_post

        thumb_url = getattr(cover_post, "primary_image_url", None) or getattr(cover_post, "image", None)
        if not thumb_url:
            thumb_url = "https://placehold.co/1200x800/0f0f14/ffffff?text=Collection"

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
    ingredients_qs = Ingredient.objects.filter(recipe_post=recipe).order_by("position")
    steps_qs = RecipeStep.objects.filter(recipe_post=recipe).order_by("position")
    images_qs = recipe.images.all()

    if not privacy_service.can_view_post(request.user, recipe):
        raise Http404("Post not available.")

    comments = recipe.comments.select_related("user").order_by("-created_at")
    user_liked = user_saved = is_following_author = False
    collections_for_modal = []

    if request.user.is_authenticated:
        user_liked = Like.objects.filter(user=request.user, recipe_post=recipe).exists()
        user_saved = FavouriteItem.objects.filter(
            favourite__user=request.user,
            recipe_post=recipe,
        ).exists()
        collections_for_modal = _collections_modal_state(request.user, recipe)
        is_following_author = Follower.objects.filter(
            follower=request.user,
            author=recipe.author,
        ).exists()

    likes_count = Like.objects.filter(recipe_post=recipe).count()

    saves_count = FavouriteItem.objects.filter(recipe_post=recipe).count()

    image_url = _primary_image_url(recipe)
    gallery_images = _gallery_images(images_qs) if images_qs.count() > 1 else []
    author_handle = getattr(recipe.author, "username", "")
    total_time = (recipe.prep_time_min or 0) + (recipe.cook_time_min or 0)
    cook_time = f"{total_time} min" if total_time else "N/A"
    serves = getattr(recipe, "serves", None) or 1
    summary = recipe.description or ""
    tags_list = recipe.tags or []
    post_date = (recipe.published_at or recipe.created_at or timezone.now()).strftime("%b %d, %Y")
    source_link = request.build_absolute_uri(reverse("recipe_detail", args=[recipe.id]))
    source_label = "Recipi"

    ingredients_all = list(ingredients_qs)
    shop_ingredients = [ing for ing in ingredients_all if getattr(ing, "shop_url", None) and ing.shop_url.strip()]
    ingredients = ingredients_all
    steps = [s.description for s in steps_qs]

    context = {
        "recipe": recipe,
        "post": recipe,
        "image_url": image_url,
        "author_handle": author_handle,
        "title": recipe.title,
        "cook_time": cook_time,
        "serves": serves,
        "ingredients": ingredients,
        "shop_ingredients": shop_ingredients,
        "steps": steps,
        "summary": summary,
        "tags": tags_list,
        "post_date": post_date,
        "source_link": source_link,
        "source_label": source_label,
        "user_liked": user_liked,
        "user_saved": user_saved,
        "is_following_author": is_following_author,
        "likes_count": likes_count,
        "saves_count": saves_count,
        "comments": comments,
        "comment_form": CommentForm(),
        "gallery_images": gallery_images,
        "video_url": None,
        "view_similar": [],
        "save_collections": collections_for_modal,
        "visibility": recipe.visibility,
    }
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
    # Determine which collection this toggle applies to.
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

    existing = FavouriteItem.objects.filter(
        favourite=favourite,
        recipe_post=recipe,
    )

    if existing.exists():
        existing.delete()
        new_count = max(0, (recipe.saved_count or 0) - 1)
        is_saved_now = False
    else:
        FavouriteItem.objects.create(
            favourite=favourite,
            recipe_post=recipe,
        )
        new_count = (recipe.saved_count or 0) + 1
        is_saved_now = True

    RecipePost.objects.filter(id=recipe.id).update(saved_count=new_count)

    is_ajax = _is_hx(request)
    if is_ajax:
        # choose a thumbnail for this collection: explicit cover_post first,
        # otherwise fall back to the current recipe that was just toggled
        cover_post = favourite.cover_post or recipe
        thumb_url = getattr(cover_post, "primary_image_url", None) or getattr(
            cover_post,
            "image",
            None,
        ) or "https://placehold.co/1200x800/0f0f14/ffffff?text=Collection"

        payload = {
            "saved": is_saved_now,
            "saved_count": new_count,
            "collection": {
                "id": str(favourite.id),
                "name": favourite.name,
                "created": created_collection,
                "thumb_url": thumb_url,
            },
        }
        return JsonResponse(payload)

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

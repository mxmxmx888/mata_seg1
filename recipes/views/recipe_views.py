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
from recipes.models import RecipePost, Like, Comment, Follower, Ingredient
import json
from recipes.models.favourite_item import FavouriteItem

from recipes.views.recipe_view_helpers import (
    build_recipe_context,
    collection_thumb,
    is_hx,
    primary_image_url,
    gallery_images,
    collections_modal_state,
    resolve_collection,
    set_primary_image,
    toggle_save,
)

# Backwards-compatible exports for tests expecting old helper names
_is_hx = is_hx
_collection_thumb = collection_thumb
_primary_image_url = primary_image_url
_collections_modal_state = collections_modal_state
_gallery_images = gallery_images

User = get_user_model()
privacy_service = PrivacyService()
follow_service_factory = FollowService


@login_required
def recipe_create(request):
    """Create a new recipe post from a submitted RecipePostForm."""
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
        set_primary_image(recipe)
        return redirect("recipe_detail", post_id=recipe.id)

    response = render(
        request,
        "app/create_recipe.html",
        {
            "form": form,
            "exclude_fields": ["shop_images"],  # render form fields except shopping images (handled manually)
        },
    )
    response["Cache-Control"] = "no-store, must-revalidate"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response

@login_required
def recipe_edit(request, post_id):
    """Edit an existing recipe post owned by the current user."""
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
        set_primary_image(recipe)
        messages.success(request, "Recipe updated.")
        detail_url = reverse("recipe_detail", kwargs={"post_id": recipe.id})
        return redirect(f"{detail_url}?from_edit=1")

    shopping_items = [
        {
            "name": ing.name,
            "url": ing.shop_url or "",
            "image_url": ing.shop_image_upload.url if ing.shop_image_upload else "",
        }
        for ing in Ingredient.objects.filter(recipe_post=recipe, shop_url__isnull=False).order_by("position")
    ]
    return render(
        request,
        "app/edit_recipe.html",
        {
            "form": form,
            "recipe": recipe,
            # render form fields except images (kept as-is on edit) and shopping images (handled manually)
            "exclude_fields": ["images", "shop_images"],
            "shopping_items_data": shopping_items,
            "shopping_items_json": json.dumps(shopping_items),
        },
    )

@login_required
def recipe_detail(request, post_id):
    """Display a single recipe post if the viewer is allowed."""
    recipe = get_object_or_404(RecipePost, id=post_id)

    if not privacy_service.can_view_post(request.user, recipe):
        raise Http404("Post not available.")

    comments_qs = recipe.comments.select_related("user").order_by("-created_at")
    page_size = 50
    page_number = max(1, int(request.GET.get("comments_page") or 1))
    start = (page_number - 1) * page_size
    end = start + page_size
    comments_page = list(comments_qs[start:end])
    has_more_comments = comments_qs.count() > end

    if request.headers.get("HX-Request") and request.GET.get("comments_only") == "1":
        return render(
            request,
            "partials/post/comment_items.html",
            {"comments": comments_page, "request": request},
        )

    context = build_recipe_context(recipe, request.user, comments_page)
    context.update(
        {
            "comments_has_more": has_more_comments,
            "comments_next_page": page_number + 1 if has_more_comments else None,
        }
    )
    # Ensure source_link is absolute for sharing
    context["source_link"] = request.build_absolute_uri(context["source_link"])
    return render(request, "post/post_detail.html", context)

@login_required
def saved_recipes(request):
    """List all unique recipes saved by the current user."""
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
    """Delete a recipe post owned by the current user."""
    recipe = get_object_or_404(RecipePost, id=post_id, author=request.user)

    if request.method == "POST":
        recipe.delete()
        messages.success(request, "Recipe deleted.")
        return redirect("profile")

    return redirect("recipe_detail", post_id=recipe.id)

@login_required
def toggle_favourite(request, post_id):
    """Toggle save/unsave for a recipe and return HX JSON or redirect."""
    recipe = get_object_or_404(RecipePost, id=post_id)
    favourite, created_collection = resolve_collection(request, recipe)
    is_saved_now, new_count = toggle_save(favourite, recipe)
    RecipePost.objects.filter(id=recipe.id).update(saved_count=new_count)

    if is_hx(request):
        return JsonResponse(
            {
                "saved": is_saved_now,
                "saved_count": new_count,
                "collection": {
                    "id": str(favourite.id),
                    "name": favourite.name,
                    "created": created_collection,
                    "thumb_url": collection_thumb(favourite.cover_post, recipe),
                },
            }
        )

    return redirect(request.META.get("HTTP_REFERER") or reverse("recipe_detail", args=[recipe.id]))

@login_required
def toggle_like(request, post_id):
    """Toggle like/unlike for a recipe and return HX or redirect."""
    recipe = get_object_or_404(RecipePost, id=post_id)
    existing = Like.objects.filter(user=request.user, recipe_post=recipe)

    if existing.exists():
        existing.delete()
    else:
        Like.objects.create(user=request.user, recipe_post=recipe)

    if is_hx(request):
        return HttpResponse(status=204)

    return redirect(request.META.get("HTTP_REFERER") or reverse("recipe_detail", args=[recipe.id]))

@login_required
def toggle_follow(request, username):
    """Follow/unfollow another user, ignoring self-follow attempts."""
    target_user = get_object_or_404(User, username=username)

    if target_user == request.user:
        if request.headers.get("HX-Request") or request.headers.get("x-requested-with") == "XMLHttpRequest":
            return HttpResponse(status=204)
        return redirect(request.META.get("HTTP_REFERER") or reverse("dashboard"))

    service = follow_service_factory(request.user)
    result = service.toggle_follow(target_user)

    if is_hx(request):
        return HttpResponse(status=204)

    return redirect(request.META.get("HTTP_REFERER") or reverse("dashboard"))

@login_required
def add_comment(request, post_id):
    """Create a new comment on a recipe for the current user."""
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
    """Delete the current user's comment by id."""
    comment = get_object_or_404(Comment, id=comment_id)
    if comment.user != request.user:
        messages.error(request, "You are not allowed to delete this comment.")
        return redirect('recipe_detail', post_id=comment.recipe_post.id)
    post_id = comment.recipe_post.id
    comment.delete()
    messages.success(request, "Comment deleted.")
    return redirect('recipe_detail', post_id=post_id)

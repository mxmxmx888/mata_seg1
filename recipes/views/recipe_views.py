"""Views for creating, viewing, and interacting with recipe posts."""

import json
from dataclasses import dataclass

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from recipes.forms.recipe_forms import RecipePostForm
from recipes.forms.comment_form import CommentForm
from recipes.services import PrivacyService, FollowService
from recipes.services.recipe_posts import (
    RecipeContentService,
    RecipeEngagementService,
)
from recipes.services.comments import CommentService

from recipes.views.recipe_view_helpers import (
    build_recipe_context,
    collection_thumb,
    is_hx,
    primary_image_url,
    gallery_images,
    collections_modal_state,
)

# Backwards-compatible exports for tests expecting old helper names
_is_hx = is_hx
_collection_thumb = collection_thumb
_primary_image_url = primary_image_url
_collections_modal_state = collections_modal_state
_gallery_images = gallery_images

User = get_user_model()
# Compatibility export for tests patching this symbol
follow_service_factory = FollowService


@dataclass(frozen=True)
class RecipeViewDeps:
    privacy_service: object
    follow_service_factory: object
    content_service: object
    engagement_service: object
    comment_service: object


def _deps():
    """Provide injectable dependencies for recipe views."""
    return RecipeViewDeps(
        privacy_service=PrivacyService(),
        follow_service_factory=follow_service_factory,
        content_service=RecipeContentService(),
        engagement_service=RecipeEngagementService(),
        comment_service=CommentService(),
    )


@login_required
def recipe_create(request):
    """Create a new recipe post from a submitted RecipePostForm."""
    deps = _deps()
    form = RecipePostForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        recipe = deps.content_service.create_from_form(form, request.user)
        deps.content_service.persist_relations(form, recipe)
        return redirect("recipe_detail", post_id=recipe.id)

    return _render_create_form(request, form)

@login_required
def recipe_edit(request, post_id):
    """Edit an existing recipe post owned by the current user."""
    deps = _deps()
    recipe = deps.content_service.fetch_owned_post(request.user, post_id)
    form = RecipePostForm(request.POST or None, request.FILES or None, instance=recipe)
    if request.method == "POST" and form.is_valid():
        deps.content_service.update_from_form(recipe, form)
        deps.content_service.persist_relations(form, recipe)
        messages.success(request, "Recipe updated.")
        detail_url = reverse("recipe_detail", kwargs={"post_id": recipe.id})
        return redirect(f"{detail_url}?from_edit=1")

    shopping_items = deps.content_service.shopping_items_for(recipe)
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
    deps = _deps()
    recipe = deps.content_service.fetch_post(post_id)

    if not deps.privacy_service.can_view_post(request.user, recipe):
        raise Http404("Post not available.")

    comments_page, has_more_comments, page_number = _comments_page(recipe, request)
    if request.headers.get("HX-Request") and request.GET.get("comments_only") == "1":
        return render(request, "partials/post/comment_items.html", {"comments": comments_page, "request": request})

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

def _render_create_form(request, form):
    """Render the create recipe form with cache-busting headers."""
    response = render(
        request,
        "app/create_recipe.html",
        {"form": form, "exclude_fields": ["shop_images"]},
    )
    response["Cache-Control"] = "no-store, must-revalidate"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response

def _comments_page(recipe, request, page_size=50):
    """Return a slice of comments for a recipe along with pagination metadata."""
    deps = _deps()
    return deps.content_service.comments_page(recipe, request, page_size)

@login_required
def saved_recipes(request):
    """List all unique recipes saved by the current user."""
    deps = _deps()
    posts = deps.engagement_service.saved_posts_for_user(request.user)
    return render(request, "app/saved_recipes.html", {"posts": posts})

@login_required
def delete_my_recipe(request, post_id):
    """Delete a recipe post owned by the current user."""
    deps = _deps()
    recipe = deps.content_service.fetch_owned_post(request.user, post_id)

    if request.method == "POST":
        recipe.delete()
        messages.success(request, "Recipe deleted.")
        return redirect("profile")

    return redirect("recipe_detail", post_id=recipe.id)

@login_required
def toggle_favourite(request, post_id):
    """Toggle save/unsave for a recipe and return HX JSON or redirect."""
    deps = _deps()
    recipe = deps.content_service.fetch_post(post_id)
    collection_id = request.POST.get("collection_id") or request.GET.get("collection_id")
    collection_name = request.POST.get("collection_name") or request.GET.get("collection_name")
    is_saved_now, new_count, collection = deps.engagement_service.toggle_favourite(
        request.user,
        recipe,
        collection_id=collection_id,
        collection_name=collection_name,
    )

    if is_hx(request):
        return JsonResponse(
            {
                "saved": is_saved_now,
                "saved_count": new_count,
                "collection": collection,
            }
        )

    return redirect(request.META.get("HTTP_REFERER") or reverse("recipe_detail", args=[recipe.id]))

@login_required
def toggle_like(request, post_id):
    """Toggle like/unlike for a recipe and return HX or redirect."""
    deps = _deps()
    recipe = deps.content_service.fetch_post(post_id)
    deps.engagement_service.toggle_like(request.user, recipe)

    if is_hx(request):
        return HttpResponse(status=204)

    return redirect(request.META.get("HTTP_REFERER") or reverse("recipe_detail", args=[recipe.id]))

@login_required
def toggle_follow(request, username):
    """Follow/unfollow another user, ignoring self-follow attempts."""
    deps = _deps()
    target_user = get_object_or_404(User, username=username)

    if target_user == request.user:
        return _self_follow_response(request)

    service = deps.follow_service_factory(request.user)
    result = service.toggle_follow(target_user)

    if is_hx(request):
        return HttpResponse(status=204)

    return redirect(request.META.get("HTTP_REFERER") or reverse("dashboard"))

@login_required
def add_comment(request, post_id):
    """Create a new comment on a recipe for the current user."""
    deps = _deps()
    recipe = deps.content_service.fetch_post(post_id)
    if request.method == "POST":
        form = CommentForm(request.POST)
        if deps.comment_service.create_comment(recipe, request.user, form):
            messages.success(request, "Comment posted.")
        else:
            messages.error(request, "Error posting comment.")
    
    return redirect("recipe_detail", post_id=recipe.id)

@login_required
def delete_comment(request, comment_id):
    """Delete the current user's comment by id."""
    deps = _deps()
    comment = deps.comment_service.fetch(comment_id)
    if not deps.comment_service.can_delete(comment, request.user):
        messages.error(request, "You are not allowed to delete this comment.")
        return redirect('recipe_detail', post_id=comment.recipe_post.id)
    post_id = deps.comment_service.delete_comment(comment)
    messages.success(request, "Comment deleted.")
    return redirect('recipe_detail', post_id=post_id)


def _self_follow_response(request):
    """Return appropriate response when a user attempts to follow themselves."""
    if request.headers.get("HX-Request") or request.headers.get("x-requested-with") == "XMLHttpRequest":
        return HttpResponse(status=204)
    return redirect(request.META.get("HTTP_REFERER") or reverse("dashboard"))

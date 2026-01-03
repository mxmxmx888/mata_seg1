from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from recipes.forms.favourite_form import FavouriteForm
from recipes.services.favourites import FavouriteService
from recipes.views.profile_data_helpers import collections_for_user, profile_data_for_user
from recipes.views.view_utils import is_ajax_request
from recipes.views.profile_view import FavouriteItem

favourite_service = FavouriteService()


@login_required
def collections_overview(request):
    """Render the current user's collections list page."""
    page_size = 35
    page_number = max(1, int(request.GET.get("page") or 1))
    collections_all = collections_for_user(request.user)
    has_collections = bool(collections_all)
    start = (page_number - 1) * page_size
    end = start + page_size
    collections_page = collections_all[start:end]
    has_more = len(collections_all) > end
    if is_ajax_request(request):
        return render(
            request,
            "partials/collections/collection_cards.html",
            {"collections": collections_page, "request": request},
        )

    context = {
        "profile": profile_data_for_user(request.user),
        "collections": collections_page,
        "collections_has_more": has_more,
        "collections_next_page": page_number + 1 if has_more else None,
        "has_collections": has_collections,
    }
    return render(request, "app/collections.html", context)


@login_required
def collection_detail(request, slug):
    """Render a single collection with its saved posts."""
    favourite = favourite_service.fetch_for_user(slug, request.user)
    posts = favourite_service.posts_for(favourite)
    collection = _collection_payload(favourite, posts)
    collection_columns = _distribute_posts(posts)

    context = {
        "profile": profile_data_for_user(request.user),
        "collection": collection,
        "collection_form": FavouriteForm(initial={"name": favourite.name}),
        "posts": posts,
        "collection_columns": collection_columns,
    }
    return render(request, "app/collection_detail.html", context)


@login_required
@require_POST
def delete_collection(request, slug):
    """Delete a collection; return JSON for HX or redirect otherwise."""
    favourite = favourite_service.fetch_for_user(slug, request.user)
    favourite_service.delete(favourite)

    if is_ajax_request(request):
        return JsonResponse({"deleted": True})

    return redirect(reverse("collections"))


@login_required
@require_POST
def update_collection(request, slug):
    """Update a collection title; supports HX JSON and regular redirect paths."""
    favourite = favourite_service.fetch_for_user(slug, request.user)
    data = request.POST.copy()
    name_val = (data.get("name") or data.get("title") or "").strip()

    if not name_val:
        return _collection_response(request, favourite)

    data["name"] = name_val
    form = FavouriteForm(data or None, instance=favourite)
    if form.is_valid():
        favourite_service.update_name(favourite, form.cleaned_data["name"])
        return _collection_response(request, favourite)

    if is_ajax_request(request):
        return JsonResponse({"errors": form.errors}, status=400)
    return redirect(reverse("collection_detail", kwargs={"slug": favourite.id}))

def _collection_payload(favourite, posts):
    return {
        "id": str(favourite.id),
        "slug": str(favourite.id),
        "title": favourite.name,
        "description": "",
        "followers": 0,
        "items": posts,
    }

def _distribute_posts(posts, num_columns=5):
    columns = [[] for _ in range(num_columns)]
    for idx, post in enumerate(posts):
        columns[idx % num_columns].append(post)
    return columns

def _collection_response(request, favourite):
    payload = {"id": str(favourite.id), "title": favourite.name}
    if is_ajax_request(request):
        return JsonResponse(payload)
    return redirect(reverse("collection_detail", kwargs={"slug": favourite.id}))

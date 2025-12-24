from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from recipes.forms.favourite_form import FavouriteForm
from recipes.models import Favourite
from recipes.models.favourite_item import FavouriteItem
from recipes.views.profile_data_helpers import collections_for_user, profile_data_for_user
from recipes.views.view_utils import is_ajax_request


@login_required
def collections_overview(request):
    """Render the current user's collections list page."""
    page_size = 20
    page_number = max(1, int(request.GET.get("page") or 1))
    collections_all = collections_for_user(request.user)
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
    }
    return render(request, "app/collections.html", context)


@login_required
def collection_detail(request, slug):
    """Render a single collection with its saved posts."""
    try:
        favourite = Favourite.objects.get(id=slug, user=request.user)
    except Favourite.DoesNotExist:
        raise Http404()

    items_qs = FavouriteItem.objects.filter(favourite=favourite).select_related("recipe_post")
    if hasattr(items_qs, "order_by"):
        items_qs = items_qs.order_by("-added_at", "-id")
    posts = [item.recipe_post for item in items_qs if item.recipe_post]

    collection = {
        "id": str(favourite.id),
        "slug": str(favourite.id),
        "title": favourite.name,
        "description": "",
        "followers": 0,
        "items": posts,
    }

    # Distribute posts into 5 masonry columns (row-wise across the page)
    num_columns = 5
    collection_columns = [[] for _ in range(num_columns)]
    for idx, post in enumerate(posts):
        collection_columns[idx % num_columns].append(post)

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
    favourite = get_object_or_404(Favourite, id=slug, user=request.user)
    favourite.delete()

    if is_ajax_request(request):
        return JsonResponse({"deleted": True})

    return redirect(reverse("collections"))


@login_required
@require_POST
def update_collection(request, slug):
    """Update a collection title; supports HX JSON and regular redirect paths."""
    favourite = get_object_or_404(Favourite, id=slug, user=request.user)
    data = request.POST.copy()
    name_val = (data.get("name") or data.get("title") or "").strip()

    # If no new name provided, keep existing title and return current payload.
    if not name_val:
        payload = {
            "id": str(favourite.id),
            "title": favourite.name,
        }
        if is_ajax_request(request):
            return JsonResponse(payload)
        return redirect(reverse("collection_detail", kwargs={"slug": favourite.id}))

    # Normal update path via Django form validation.
    data["name"] = name_val
    form = FavouriteForm(data or None, instance=favourite)

    if form.is_valid():
        form.save()
        payload = {
            "id": str(favourite.id),
            "title": favourite.name,
        }
        if is_ajax_request(request):
            return JsonResponse(payload)
        return redirect(reverse("collection_detail", kwargs={"slug": favourite.id}))

    if is_ajax_request(request):
        return JsonResponse({"errors": form.errors}, status=400)
    return redirect(reverse("collection_detail", kwargs={"slug": favourite.id}))

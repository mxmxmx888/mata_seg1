from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from recipes.models import Favourite
from recipes.models.favourite_item import FavouriteItem
from recipes.views.profile_data_helpers import collections_for_user, profile_data_for_user
from recipes.views.view_utils import is_ajax_request


@login_required
def collections_overview(request):
    context = {
        "profile": profile_data_for_user(request.user),
        "collections": collections_for_user(request.user),
    }
    return render(request, "app/collections.html", context)


@login_required
def collection_detail(request, slug):
    try:
        favourite = Favourite.objects.get(id=slug, user=request.user)
    except Favourite.DoesNotExist:
        raise Http404()

    items_qs = FavouriteItem.objects.filter(favourite=favourite).select_related("recipe_post")
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
        "posts": posts,
        "collection_columns": collection_columns,
    }
    return render(request, "app/collection_detail.html", context)


@login_required
@require_POST
def delete_collection(request, slug):
    favourite = get_object_or_404(Favourite, id=slug, user=request.user)
    favourite.delete()

    if is_ajax_request(request):
        return JsonResponse({"deleted": True})

    return redirect(reverse("collections"))


@login_required
@require_POST
def update_collection(request, slug):
    favourite = get_object_or_404(Favourite, id=slug, user=request.user)
    new_title = (request.POST.get("title") or request.POST.get("name") or "").strip()

    if new_title:
        favourite.name = new_title
        favourite.save(update_fields=["name"])

    payload = {
        "id": str(favourite.id),
        "title": favourite.name,
    }
    if is_ajax_request(request):
        return JsonResponse(payload)

    return redirect(reverse("collection_detail", kwargs={"slug": favourite.id}))

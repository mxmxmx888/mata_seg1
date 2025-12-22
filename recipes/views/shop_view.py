import hashlib
import secrets

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from recipes.models import Ingredient
from recipes.models import RecipePost
from recipes.services import PrivacyService

privacy_service = PrivacyService()

@login_required
def shop(request):
    seed = request.GET.get("seed") or secrets.token_hex(8)
    items_qs = (
        Ingredient.objects.filter(
            Q(shop_url__isnull=False) & ~Q(shop_url__regex=r'^\s*$')
        )
        .select_related("recipe_post")
    )

    visible_posts = privacy_service.filter_visible_posts(
        RecipePost.objects.filter(id__in=items_qs.values_list("recipe_post_id", flat=True).distinct()),
        request.user,
    ).values_list("id", flat=True)
    items_qs = items_qs.filter(recipe_post_id__in=visible_posts)

    item_ids = list(items_qs.values_list("id", flat=True))
    shuffled_ids = sorted(
        item_ids, key=lambda pk: hashlib.sha256(f"{seed}-{pk}".encode("utf-8")).hexdigest()
    )

    paginator = Paginator(shuffled_ids, 24)
    page_number = request.GET.get("page") or 1
    page_obj = paginator.get_page(page_number)

    current_ids = list(page_obj.object_list)
    id_positions = {pk: idx for idx, pk in enumerate(current_ids)}
    current_items = (
        sorted(
            items_qs.filter(id__in=current_ids),
            key=lambda obj: id_positions.get(obj.id, 0),
        )
        if current_ids
        else []
    )
    page_obj.object_list = current_items

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("ajax") == "1"

    if is_ajax:
        shop_item_list = render_to_string(
            "partials/shop/shop_items.html",
            {"items": page_obj.object_list},
            request=request,
        )
        return JsonResponse(
            {
                "shop_item_list": shop_item_list,  # preserved key for existing JS/tests
                "html": shop_item_list,
                "has_next": page_obj.has_next(),
            }
        )


    context = {
        "items": page_obj.object_list,
        "page_obj": page_obj,
        "seed": seed,
    }
    return render(request, "app/shop.html", context)

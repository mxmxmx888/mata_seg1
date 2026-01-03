import secrets

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from recipes.services.shop import ShopService
from recipes.utils.http import is_ajax


def _deps():
    """Provide injectable dependencies for shop views."""
    return {"shop_service": ShopService()}


@login_required
def shop(request):
    """Display shoppable ingredients with deterministic shuffle/pagination."""
    deps = _deps()
    seed = request.GET.get("seed") or secrets.token_hex(8)
    page_number = request.GET.get("page") or 1
    page_obj = deps["shop_service"].paginated_shuffled_items(request.user, seed, page_number)
    if is_ajax(request):
        return _shop_ajax_response(request, page_obj)
    return render(request, "app/shop.html", {"items": page_obj.object_list, "page_obj": page_obj, "seed": seed})


def _shop_ajax_response(request, page_obj):
    shop_item_list = render_to_string(
        "partials/shop/shop_items.html",
        {"items": page_obj.object_list},
        request=request,
    )
    return JsonResponse(
        {
            "shop_item_list": shop_item_list,
            "html": shop_item_list,
            "has_next": page_obj.has_next(),
        }
    )

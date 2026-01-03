import secrets

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from recipes.services.shop import ShopService

shop_service = ShopService()


@login_required
def shop(request):
    """Display shoppable ingredients with deterministic shuffle/pagination."""
    seed = request.GET.get("seed") or secrets.token_hex(8)
    page_number = request.GET.get("page") or 1
    page_obj = shop_service.paginated_shuffled_items(request.user, seed, page_number)
    if _is_ajax(request):
        return _shop_ajax_response(request, page_obj)
    return render(request, "app/shop.html", {"items": page_obj.object_list, "page_obj": page_obj, "seed": seed})


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("ajax") == "1"


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

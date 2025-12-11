from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from recipes.models import Ingredient

@login_required
def shop(request):
    items_qs = (
        Ingredient.objects.filter(
            Q(shop_url__isnull=False) & ~Q(shop_url__regex=r'^\s*$')
        )
        .select_related("recipe_post")
        .order_by("-id")
    )

    paginator = Paginator(items_qs, 24)
    page_number = request.GET.get("page") or 1
    page_obj = paginator.get_page(page_number)

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("ajax") == "1"

    if is_ajax:
        html = render_to_string(
            "partials/shop_items.html",
            {"items": page_obj.object_list},
            request=request,
        )
        return JsonResponse(
            {
                "html": html,
                "has_next": page_obj.has_next(),
            }
        )

    context = {
        "items": page_obj.object_list,
        "page_obj": page_obj,
    }
    return render(request, "shop.html", context)

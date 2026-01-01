"""Dashboard view helpers for discovery feed, search scopes, and AJAX fragments."""

from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET
from recipes.views.dashboard_params import (
    parse_dashboard_params,
    get_for_you_seed,
    _ensure_for_you_seed,
    _safe_offset,
)
from recipes.views.dashboard_utils import feed_service, privacy_service

try:
    from recipes.models import Ingredient, RecipePost
except Exception:  # pragma: no cover
    from recipes.models.ingredient import Ingredient
    from recipes.models.recipe_post import RecipePost


FEED_PAGE_LIMIT = 24


def _discover_queryset(params, user, privacy):
    """Build the discovery queryset with all filters applied."""
    return feed_service.discover_queryset(
        user,
        query=params["q"],
        category=params["category"],
        ingredient_q=params["ingredient_q"],
        have_ingredients_list=params["have_ingredients_list"],
        min_prep=params["min_prep"],
        max_prep=params["max_prep"],
        sort=params["sort"],
        privacy=privacy,
    )


def _for_you_ajax_response(request, seed, privacy):
    """Return the JSON payload for the 'for you' infinite scroll."""
    limit = FEED_PAGE_LIMIT
    offset = _safe_offset(request.GET.get("for_you_offset"))
    seed = _ensure_for_you_seed(request, seed)
    posts = feed_service.for_you_posts(request.user, limit=limit, offset=offset, seed=seed, privacy=privacy)
    html = render_to_string("partials/feed/feed_cards.html", {"posts": posts, "request": request}, request=request)
    return JsonResponse(
        {"html": html, "has_more": len(posts) == limit, "count": len(posts)}
    )


def _following_ajax_response(request):
    """Return the JSON payload for the 'following' infinite scroll."""
    limit = FEED_PAGE_LIMIT
    offset = _safe_offset(request.GET.get("following_offset"))
    posts = feed_service.following_posts(request.user, limit=limit, offset=offset)
    html = render_to_string("partials/feed/feed_cards.html", {"posts": posts, "request": request}, request=request)
    return JsonResponse(
        {"html": html, "has_more": len(posts) == limit, "count": len(posts)}
    )


def _shopping_search(request, params, privacy):
    """Return shopping results or an AJAX fragment when scope=shopping."""
    items_qs = _shopping_items_queryset(request.user, params, privacy)
    paginator = Paginator(items_qs, 24)
    page_obj = paginator.get_page(params["page_number"])
    if params["is_ajax"]:
        html = render_to_string(
            "partials/shop/shop_items.html",
            {"items": page_obj.object_list},
            request=request,
        )
        return JsonResponse(
            {
                "html": html,
                "has_next": page_obj.has_next(),
            }
        ), None, None, None

    return None, list(page_obj.object_list), page_obj.has_next(), page_obj.number


def _shopping_items_queryset(user, params, privacy):
    """Return a filtered queryset of shopping items visible to the user."""
    qs = (
        Ingredient.objects.filter(
            Q(shop_url__isnull=False) & ~Q(shop_url__regex=r"^\s*$")
        )
        .select_related("recipe_post")
        .order_by("-id")
    )
    visible_posts = privacy.filter_visible_posts(
        RecipePost.objects.filter(
            id__in=qs.values_list("recipe_post_id", flat=True).distinct()
        ),
        user,
    ).values_list("id", flat=True)
    qs = qs.filter(recipe_post_id__in=visible_posts)
    if params["q"]:
        qs = qs.filter(Q(name__icontains=params["q"])).distinct()
    return qs


def _recipe_search(request, params, discover_qs):
    """Paginate and optionally return AJAX HTML for recipe search results."""
    paginator = Paginator(discover_qs, 18)
    page_obj = paginator.get_page(params["page_number"])

    if params["is_ajax"]:
        html = render_to_string(
            "partials/feed/feed_cards.html",
            {"posts": page_obj.object_list, "request": request},
            request=request,
        )
        return JsonResponse(
            {
                "html": html,
                "has_next": page_obj.has_next(),
            }
        ), None, None

    return None, list(page_obj.object_list), page_obj.has_next()


def _scope_users_results(params):
    """Return user search results for the dashboard scope=users."""
    return feed_service.search_users(params["q"], limit=18)


def _scope_shopping_results(request, params, privacy):
    """Return shopping scope results or AJAX payload."""
    return _shopping_search(request, params, privacy)


def _scope_recipes_results(request, params, discover_qs):
    """Return recipe scope results or AJAX payload."""
    return _recipe_search(request, params, discover_qs)


def _default_feed(discover_qs, request, for_you_seed, privacy):
    """Build default feed bundles when no search filters are applied."""
    popular_recipes = list(discover_qs[:18])
    for_you_posts = feed_service.for_you_posts(request.user, seed=for_you_seed, privacy=privacy, limit=FEED_PAGE_LIMIT)
    following_posts = feed_service.following_posts(request.user, limit=FEED_PAGE_LIMIT)
    return popular_recipes, for_you_posts, following_posts


def _shopping_context(shopping_items, shopping_has_next, shopping_page):
    """Shape context for shopping search results."""
    return {
        "shopping_items": shopping_items,
        "shopping_has_next": shopping_has_next,
        "shopping_page_number": shopping_page,
    }


def _feed_context(pops, for_you_posts, following_posts, popular_has_next):
    """Shape feed-related context (popular, for-you, following, users)."""
    popular_recipes, users_results = pops
    return {
        "popular_recipes": popular_recipes,
        "popular_has_next": popular_has_next,
        "for_you_posts": for_you_posts,
        "following_posts": following_posts,
        "users_results": users_results,
    }


def _handle_dashboard_scope(request, params, privacy, discover_qs, for_you_seed):
    """Branch dashboard rendering based on scope (default, users, shopping, recipes)."""
    if not params["has_search"]:
        popular_recipes, for_you_posts, following_posts = _default_feed(discover_qs, request, for_you_seed, privacy)
        return None, (popular_recipes, False, [], [], False, params["page_number"], for_you_posts, following_posts)

    if params["scope"] == "users":
        return None, ([], False, _scope_users_results(params), [], False, params["page_number"], [], [])

    if params["scope"] == "shopping":
        response, shopping_items, shopping_has_next, shopping_page = _scope_shopping_results(
            request, params, privacy
        )
        if response:
            return response, None
        return None, ([], False, [], shopping_items, shopping_has_next, shopping_page, [], [])

    response, popular_recipes, popular_has_next = _scope_recipes_results(request, params, discover_qs)
    if response:
        return response, None
    return None, (popular_recipes, popular_has_next, [], [], False, params["page_number"], [], [])


def _dashboard_context(params, request, data, popular_has_next):
    """Assemble the full dashboard template context."""
    popular_recipes, users_results, shopping_items, shopping_has_next, shopping_page, for_you_posts, following_posts = data
    return {
        "current_user": request.user,
        "search_query": params["q"],
        **_feed_context((popular_recipes, users_results), for_you_posts, following_posts, popular_has_next),
        "category": params["category"],
        "ingredient": params["ingredient_q"],
        "sort": params["sort"],
        "has_search": params["has_search"],
        "scope": params["scope"],
        "have_ingredients": params["have_ingredients_raw"],
        **_shopping_context(shopping_items, shopping_has_next, shopping_page),
    }


def _build_dashboard(request, params, privacy, for_you_seed):
    """Compute dashboard context or AJAX responses based on parsed params."""
    discover_qs = _discover_queryset(params, request.user, privacy)
    response, data = _handle_dashboard_scope(request, params, privacy, discover_qs, for_you_seed)
    if response:
        return response, None
    popular_recipes, popular_has_next, users_results, shopping_items, shopping_has_next, shopping_page, for_you_posts, following_posts = data
    context = _dashboard_context(
        params,
        request,
        (
            popular_recipes,
            users_results,
            shopping_items,
            shopping_has_next,
            shopping_page,
            for_you_posts,
            following_posts,
        ),
        popular_has_next,
    )
    return None, context


@require_GET
def dashboard(request):
    """Render the main dashboard with feed, search, and filters."""
    if not request.user.is_authenticated:  # pragma: no cover - guarded by URL config
        return render(request, "auth/discover_logged_out.html")

    params = parse_dashboard_params(request)
    privacy = privacy_service
    for_you_seed = get_for_you_seed(request, params["for_you_ajax"])

    if params["following_ajax"]:
        return _following_ajax_response(request)

    if params["for_you_ajax"]:
        return _for_you_ajax_response(request, for_you_seed, privacy)

    response, context = _build_dashboard(request, params, privacy, for_you_seed)
    if response:  # pragma: no cover - AJAX paths handled earlier
        return response
    return render(request, "app/dashboard.html", context)

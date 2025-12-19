import random
import re
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from django.db.models import Q, F, ExpressionWrapper, IntegerField, Exists, OuterRef
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET
from .dashboard_utils import (
    privacy_service,
    _normalise_tags,
    _user_preference_tags,
    _base_posts_queryset,
    _score_post_for_user,
    _get_for_you_posts,
    _get_following_posts,
    _search_users,
    _filter_posts_by_prep_time,
    Like,
)
try:
    from recipes.models import RecipePost, Ingredient
except Exception:
    from recipes.models.recipe_post import RecipePost
    from recipes.models.ingredient import Ingredient

@require_GET
def dashboard(request):
    if not request.user.is_authenticated:
        return render(request, "auth/discover_logged_out.html")

    privacy = privacy_service

    for_you_seed = request.session.get("for_you_seed")
    if request.GET.get("for_you_ajax") != "1":
        for_you_seed = random.random()
        request.session["for_you_seed"] = for_you_seed

    q = (request.GET.get("q") or "").strip()
    scope = (request.GET.get("scope") or "recipes").strip().lower()
    if scope not in ("recipes", "users", "shopping"):
        scope = "recipes"
    category = (request.GET.get("category") or "all").strip()
    ingredient_q = (request.GET.get("ingredient") or "").strip()
    sort = (request.GET.get("sort") or "newest").strip()
    mode = (request.GET.get("mode") or "feed").strip()

    min_prep = (request.GET.get("min_prep") or "").strip()
    max_prep = (request.GET.get("max_prep") or "").strip()

    have_ingredients_raw = (request.GET.get("have_ingredients") or "").strip()
    have_ingredients_list = []
    if have_ingredients_raw:
        tokens = re.split(r"[,\n]+", have_ingredients_raw)
        have_ingredients_list = [
            t.strip().lower() for t in tokens if t.strip()
        ]

    has_search = (
        mode == "search"
        or bool(q or ingredient_q or have_ingredients_list or min_prep or max_prep or (category and category != "all"))
    )
    page_number = int(request.GET.get("page") or 1)
    if page_number < 1:
        page_number = 1

    is_ajax = (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or request.GET.get("ajax") == "1"
    )

    discover_qs = (
        RecipePost.objects.filter(published_at__isnull=False)
        .select_related("author")
    )

    if request.user.is_authenticated:
        discover_qs = discover_qs.exclude(
            Q(tags__icontains="#private") & ~Q(author=request.user)
        )

    if q:
        discover_qs = discover_qs.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(tags__icontains=q)
        ).distinct()

    if category and category != "all":
        discover_qs = discover_qs.filter(category__iexact=category)

    if ingredient_q:
        discover_qs = discover_qs.filter(
            ingredients__name__icontains=ingredient_q.lower()
        ).distinct()

    if min_prep or max_prep:
        total_time_expr = ExpressionWrapper(
            F("prep_time_min") + F("cook_time_min"),
            output_field=IntegerField(),
        )
        discover_qs = discover_qs.annotate(total_time_min=total_time_expr)

        if min_prep:
            try:
                discover_qs = discover_qs.filter(total_time_min__gte=int(min_prep))
            except (TypeError, ValueError):
                pass

        if max_prep:
            try:
                discover_qs = discover_qs.filter(total_time_min__lte=int(max_prep))
            except (TypeError, ValueError):
                pass

    if have_ingredients_list:
        allowed_names = [name.lower() for name in have_ingredients_list]

        disallowed_subquery = Ingredient.objects.filter(
            recipe_post_id=OuterRef("pk")
        ).exclude(name__in=allowed_names)

        allowed_subquery = Ingredient.objects.filter(
            recipe_post_id=OuterRef("pk"),
            name__in=allowed_names,
        )

        discover_qs = discover_qs.annotate(
            has_disallowed=Exists(disallowed_subquery),
            has_allowed=Exists(allowed_subquery),
        ).filter(has_disallowed=False, has_allowed=True)

    discover_qs = privacy.filter_visible_posts(discover_qs, request.user)
    if sort == "popular":
        discover_qs = discover_qs.order_by("-saved_count", "-published_at", "-created_at")
    elif sort == "oldest":
        discover_qs = discover_qs.order_by("published_at", "created_at")
    else:
        discover_qs = discover_qs.order_by("-published_at", "-created_at")

    popular_recipes = []
    popular_has_next = False
    users_results = []
    shopping_items = []
    shopping_has_next = False
    shopping_page = page_number
    if request.GET.get("for_you_ajax") == "1":
        limit = 12
        try:
            offset = int(request.GET.get("for_you_offset") or 0)
        except (TypeError, ValueError):
            offset = 0
        if offset < 0:
            offset = 0

        if for_you_seed is None:
            for_you_seed = random.random()
            request.session["for_you_seed"] = for_you_seed

        posts = _get_for_you_posts(request.user, limit=limit, offset=offset, seed=for_you_seed, privacy=privacy)
        html = render_to_string(
            "partials/feed/feed_cards.html",
            {"posts": posts, "request": request},
            request=request,
        )
        has_more = len(posts) == limit
        return JsonResponse(
            {
                "html": html,
                "has_more": has_more,
                "count": len(posts),
            }
        )

    if has_search and scope == "users":
        users_results = _search_users(q, limit=18)
        popular_recipes = []
        for_you_posts = []
        following_posts = []
    elif has_search and scope == "shopping":
        items_qs = (
            Ingredient.objects.filter(
                Q(shop_url__isnull=False) & ~Q(shop_url__regex=r"^\s*$")
            )
            .select_related("recipe_post")
            .order_by("-id")
        )

        visible_posts = privacy.filter_visible_posts(
            RecipePost.objects.filter(
                id__in=items_qs.values_list("recipe_post_id", flat=True).distinct()
            ),
            request.user,
        ).values_list("id", flat=True)
        items_qs = items_qs.filter(recipe_post_id__in=visible_posts)
        if q:
            items_qs = items_qs.filter(
                Q(name__icontains=q)
            ).distinct()

        paginator = Paginator(items_qs, 24)
        page_obj = paginator.get_page(page_number)
        if is_ajax:
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
            )
        
        shopping_items = list(page_obj.object_list)
        shopping_has_next = page_obj.has_next()
        shopping_page = page_obj.number
        popular_recipes = []
        for_you_posts = []
        following_posts = []
        users_results = []
    elif has_search:
        paginator = Paginator(discover_qs, 18)
        page_obj = paginator.get_page(page_number)

        if is_ajax:
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
            )

        popular_recipes = list(page_obj.object_list)
        popular_has_next = page_obj.has_next()
        for_you_posts = []
        following_posts = []
    else:
        popular_recipes = list(discover_qs[:18])
        for_you_posts = _get_for_you_posts(request.user, seed=for_you_seed, privacy=privacy)
        following_posts = _get_following_posts(request.user)

    context = {
        "current_user": request.user,
        "search_query": q,
        "popular_recipes": popular_recipes,
        "for_you_posts": for_you_posts,
        "following_posts": following_posts,
        "category": category,
        "ingredient": ingredient_q,
        "sort": sort,
        "has_search": has_search,
        "popular_has_next": popular_has_next,
        "scope": scope,
        "users_results": users_results,
        "have_ingredients": have_ingredients_raw,
        "shopping_items": shopping_items,
        "shopping_has_next": shopping_has_next,
        "shopping_page_number": shopping_page,
    }
    return render(request, "app/dashboard.html", context)

import random
import re
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from django.db.models import Q, F, ExpressionWrapper, IntegerField, Exists, OuterRef
from django.utils import timezone
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_GET
from recipes.services import PrivacyService
try:
    from recipes.models import RecipePost, Favourite, FavouriteItem, Like, Follower, Ingredient
except Exception:
    from recipes.models.recipe_post import RecipePost
    from recipes.models.favourite import Favourite
    from recipes.models.favourite_item import FavouriteItem
    from recipes.models.like import Like
    from recipes.models.followers import Follower

def _normalise_tags(tags):
    if not tags:
        return []
    if isinstance(tags, str):
        parts = [p.strip() for p in tags.split(",")]
        return [p.lower() for p in parts if p]
    if isinstance(tags, list):
        return [str(t).strip().lower() for t in tags if str(t).strip()]
    return []

def _user_preference_tags(user):
    tags = []

    fav_item_qs = (
        FavouriteItem.objects
        .filter(favourite__user=user)
        .select_related("recipe_post")
    )
    like_qs = Like.objects.filter(user=user).select_related("recipe_post")

    for item in fav_item_qs:
        tags.extend(_normalise_tags(getattr(item.recipe_post, "tags", [])))

    for like in like_qs:
        tags.extend(_normalise_tags(getattr(like.recipe_post, "tags", [])))

    seen = set()
    result = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result

def _base_posts_queryset():
    return (
        RecipePost.objects.filter(published_at__isnull=False)
        .select_related("author")
        .prefetch_related("images")
        .order_by("-published_at", "-created_at")
    )

def _score_post_for_user(post, preferred_tags):
    score = 0

    post_tags = set(_normalise_tags(getattr(post, "tags", [])))
    pref_set = set(preferred_tags)

    if post_tags & pref_set:
        score += 3

    saved_count = getattr(post, "saved_count", 0) or 0
    score += saved_count

    if getattr(post, "published_at", None):
        age_days = (timezone.now() - post.published_at).days
    else:
        age_days = 999
    score += max(0, 10 - age_days)

    return score

privacy_service = PrivacyService()

def _get_for_you_posts(user, query=None, limit=12, offset=0, seed=None, privacy=privacy_service):
    qs = privacy.filter_visible_posts(_base_posts_queryset(), user)

    if query:
        qs = qs.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(tags__icontains=query)
        )

    preferred_tags = _user_preference_tags(user)

    posts = list(qs[:100])

    if preferred_tags:
        scored = [
            (_score_post_for_user(p, preferred_tags), p)
            for p in posts
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        posts = [p for _, p in scored]

    rng = random.Random(seed)
    rng.shuffle(posts)

    return posts[offset:offset + limit]

def _filter_posts_by_prep_time(posts, min_prep, max_prep):
    if min_prep is not None:
        posts = [
            p for p in posts
            if p.prep_time_min is not None and p.prep_time_min >= min_prep
        ]

    if max_prep is not None:
        posts = [
            p for p in posts
            if p.prep_time_min is not None and p.prep_time_min <= max_prep
        ]

    return posts


def _get_following_posts(user, query=None, limit=12, offset=0):
    followed_ids = list(
        Follower.objects.filter(follower=user).values_list("author_id", flat=True)
    )
    if not followed_ids:
        return []

    qs = _base_posts_queryset().filter(author_id__in=followed_ids)
    qs = privacy_service.filter_visible_posts(qs, user)

    if query:
        qs = qs.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(tags__icontains=query)
        )

    return list(qs[offset:offset + limit])

def _search_users(query, limit=18):
    User = get_user_model()
    if not query:
        return []
    return list(
        User.objects.filter(username__icontains=query)
        .order_by("username")[:limit]
    )

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
    if scope not in ("recipes", "users"):
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
            ingredients__name__icontains=q.lower()
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
            "partials/recipes/recipe_grid_items.html",
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
    elif has_search:
        paginator = Paginator(discover_qs, 18)
        page_obj = paginator.get_page(page_number)

        if is_ajax:
            html = render_to_string(
                "partials/recipes/recipe_grid_items.html",
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
    }
    return render(request, "app/dashboard.html", context)

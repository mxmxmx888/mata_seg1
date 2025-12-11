from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from django.db.models import Q
from django.utils import timezone
from django.template.loader import render_to_string

try:
    from recipes.models import RecipePost, Favourite, Like, Follower
    from recipes.models import RecipePost, Favourite, Like, Follower
except Exception:
    from recipes.models.recipe_post import RecipePost
    from recipes.models.favourite import Favourite
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

    fav_qs = Favourite.objects.filter(user=user).select_related("recipe_post")
    like_qs = Like.objects.filter(user=user).select_related("recipe_post")

    for fav in fav_qs:
        tags.extend(_normalise_tags(getattr(fav.recipe_post, "tags", [])))
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

def _get_for_you_posts(user, query=None, limit=12, offset=0):
    qs = _base_posts_queryset()

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

    return posts[offset:offset + limit]

def _get_following_posts(user, query=None, limit=12, offset=0):
    followed_ids = list(
        Follower.objects.filter(follower=user).values_list("author_id", flat=True)
    )
    if not followed_ids:
        return []

    qs = _base_posts_queryset().filter(author_id__in=followed_ids)

    if query:
        qs = qs.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(tags__icontains=query)
        )

    return list(qs[offset:offset + limit])

def dashboard(request):
    if not request.user.is_authenticated:
        return render(request, "discover_logged_out.html")

    q = (request.GET.get("q") or "").strip()
    category = (request.GET.get("category") or "all").strip()
    ingredient_q = (request.GET.get("ingredient") or "").strip()
    sort = (request.GET.get("sort") or "newest").strip()
    mode = (request.GET.get("mode") or "feed").strip()

    combined_keyword = " ".join(part for part in [q, ingredient_q] if part).strip()

    has_search = mode == "search"
    page_number = int(request.GET.get("page") or 1)
    if page_number < 1:
        page_number = 1

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("ajax") == "1"

    discover_qs = (
        RecipePost.objects.filter(published_at__isnull=False)
        .select_related("author")
    )

    if request.user.is_authenticated:
        discover_qs = discover_qs.exclude(
            Q(tags__icontains="#private") & ~Q(author=request.user)
        )

    if combined_keyword:
        discover_qs = discover_qs.filter(
            Q(title__icontains=combined_keyword)
            | Q(description__icontains=combined_keyword)
            | Q(tags__icontains=combined_keyword)
        )

    if category and category != "all":
        discover_qs = discover_qs.filter(
            tags__icontains=f"category:{category.lower()}"
        )

    if sort == "popular":
        discover_qs = discover_qs.order_by("-saved_count", "-published_at", "-created_at")
    elif sort == "oldest":
        discover_qs = discover_qs.order_by("published_at", "created_at")
    else:
        discover_qs = discover_qs.order_by("-published_at", "-created_at")

    popular_recipes = []
    popular_has_next = False

    if has_search:
        paginator = Paginator(discover_qs, 18)
        page_obj = paginator.get_page(page_number)

        if is_ajax:
            html = render_to_string(
                "partials/recipe_grid_items.html",
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
        for_you_posts = _get_for_you_posts(request.user)
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
    }
    return render(request, "dashboard.html", context)

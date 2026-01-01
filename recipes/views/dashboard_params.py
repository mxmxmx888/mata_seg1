import random
import re


def _parse_have_ingredients(request):
    """Parse have_ingredients GET param into raw string and cleaned list."""
    raw = (request.GET.get("have_ingredients") or "").strip()
    tokens = re.split(r"[,\n]+", raw) if raw else []
    return raw, [t.strip().lower() for t in tokens if t.strip()]


def _is_ajax(request):
    """Detect HTMX/explicit ajax GET flag."""
    return (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or request.GET.get("ajax") == "1"
    )


def _has_search(mode, q, ingredient_q, have_list, min_prep, max_prep, category):
    """Return True when any search filter is active."""
    return mode == "search" or bool(
        q
        or ingredient_q
        or have_list
        or min_prep
        or max_prep
        or (category and category != "all")
    )


def _normalise_scope(scope):
    """Normalise scope to recipes/users/shopping."""
    scope = (scope or "recipes").strip().lower()
    return scope if scope in ("recipes", "users", "shopping") else "recipes"


def _safe_int(value, default=1):
    """Parse a positive int with default fallback."""
    try:
        num = int(value)
    except (TypeError, ValueError):
        return default
    return num if num > 0 else default


def _safe_offset(raw_offset):
    """Parse a non-negative offset value."""
    try:
        offset = int(raw_offset or 0)
    except (TypeError, ValueError):
        return 0
    return offset if offset > 0 else 0


def _ensure_for_you_seed(request, seed):
    """Ensure a persistent per-session seed exists."""
    if seed is not None:
        return seed
    seed = random.random()
    request.session["for_you_seed"] = seed
    return seed


def parse_dashboard_params(request):
    """Extract and normalise query params for the dashboard."""
    have_ingredients_raw, have_ingredients_list = _parse_have_ingredients(request)
    q = (request.GET.get("q") or "").strip()
    ingredient_q = (request.GET.get("ingredient") or "").strip()
    min_prep = (request.GET.get("min_prep") or "").strip()
    max_prep = (request.GET.get("max_prep") or "").strip()
    category = (request.GET.get("category") or "all").strip()
    mode = (request.GET.get("mode") or "feed").strip()
    sort_raw = (request.GET.get("sort") or "").strip()
    return {
        "q": q,
        "scope": _normalise_scope(request.GET.get("scope")),
        "category": category,
        "ingredient_q": ingredient_q,
        "sort": sort_raw or "newest",
        "sort_provided": bool(sort_raw),
        "mode": mode, "min_prep": min_prep, "max_prep": max_prep,
        "have_ingredients_raw": have_ingredients_raw,
        "have_ingredients_list": have_ingredients_list,
        "has_search": _has_search(mode, q, ingredient_q, have_ingredients_list, min_prep, max_prep, category),
        "page_number": _safe_int(request.GET.get("page") or 1, default=1),
        "is_ajax": _is_ajax(request),
        "for_you_ajax": request.GET.get("for_you_ajax") == "1", "following_ajax": request.GET.get("following_ajax") == "1",
    }


def get_for_you_seed(request, for_you_ajax):
    """Return a stable seed stored in the session unless this is the first full render."""
    seed = request.session.get("for_you_seed")
    if not for_you_ajax:
        seed = random.random()
        request.session["for_you_seed"] = seed
    return seed

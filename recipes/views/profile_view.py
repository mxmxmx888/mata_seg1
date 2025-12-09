from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from recipes.forms import UserForm
from recipes.repos.post_repo import PostRepo
from recipes.repos.user_repo import UserRepo

User = get_user_model()
post_repo = PostRepo()
user_repo = UserRepo()

COMMON_COLLECTION_ITEMS = [
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1482049016688-2d3e1b311543?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1490645935967-10de6ba17061?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1481931715705-36fdd4e1bf4d?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80",
]

TRAVERSE_ITEMS = [
    "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1512058564366-18510be2db19?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1481391032119-d89fee407e44?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1521017432531-fbd92d768814?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1473093295043-cdd812d0e601?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1490645935967-10de6ba17061?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1481931715705-36fdd4e1bf4d?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80",
]

PROFILE_COLLECTIONS = [
    {
        "slug": "all-recipes",
        "title": "All Recipes",
        "count": 300,
        "privacy": "Private",
        "cover": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80",
        "items": COMMON_COLLECTION_ITEMS,
    },
    {
        "slug": "comfort-classics",
        "title": "Comfort Classics",
        "count": 65,
        "cover": "https://images.unsplash.com/photo-1473093295043-cdd812d0e601?auto=format&fit=crop&w=1200&q=80",
        "items": COMMON_COLLECTION_ITEMS,
    },
    {
        "slug": "travel-eats",
        "title": "Travel Eats",
        "count": 10,
        "cover": "https://images.unsplash.com/photo-1512058564366-18510be2db19?auto=format&fit=crop&w=1200&q=80",
        "description": "My journeys",
        "items": TRAVERSE_ITEMS,
    },
    {
        "slug": "weeknight-dinners",
        "title": "Weeknight Dinners",
        "count": 37,
        "cover": "https://images.unsplash.com/photo-1478144592103-25e218a04891?auto=format&fit=crop&w=1200&q=80",
        "items": COMMON_COLLECTION_ITEMS,
    },
    {
        "slug": "baking-basics",
        "title": "Baking Basics",
        "count": 41,
        "cover": "https://images.unsplash.com/photo-1467003909585-2f8a72700288?auto=format&fit=crop&w=1200&q=80",
        "items": COMMON_COLLECTION_ITEMS,
    },
    {
        "slug": "quick-and-easy",
        "title": "Quick & Easy",
        "count": 11,
        "cover": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80",
        "items": COMMON_COLLECTION_ITEMS,
    },
    {
        "slug": "meal-prep",
        "title": "Meal Prep",
        "count": 60,
        "cover": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80",
        "items": COMMON_COLLECTION_ITEMS,
    },
    {
        "slug": "vegetarian-favorites",
        "title": "Vegetarian Favorites",
        "count": 17,
        "cover": "https://images.unsplash.com/photo-1478145046317-39f10e56b5e9?auto=format&fit=crop&w=1200&q=80",
        "items": COMMON_COLLECTION_ITEMS,
    },
    {
        "slug": "sweet-tooth",
        "title": "Sweet Tooth",
        "count": 2,
        "cover": "https://images.unsplash.com/photo-1505253758473-96b7015fcd40?auto=format&fit=crop&w=1200&q=80",
        "items": COMMON_COLLECTION_ITEMS,
    },
    {
        "slug": "brunch-staples",
        "title": "Brunch Staples",
        "count": 16,
        "cover": "https://images.unsplash.com/photo-1490645935967-10de6ba17061?auto=format&fit=crop&w=1200&q=80",
        "items": COMMON_COLLECTION_ITEMS,
    },
    {
        "slug": "fresh-and-seasonal",
        "title": "Fresh & Seasonal",
        "count": 18,
        "cover": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80",
        "items": COMMON_COLLECTION_ITEMS,
    },
    {
        "slug": "one-pot-wonders",
        "title": "One-Pot Wonders",
        "count": 10,
        "cover": "https://images.unsplash.com/photo-1478144592103-25e218a04891?auto=format&fit=crop&w=1200&q=80",
        "items": COMMON_COLLECTION_ITEMS,
    },
]

def _profile_data_for_user(user):
    fallback_handle = "@anmzn"
    handle = user.username or fallback_handle
    display_name = user.get_full_name() or user.username or "cook"
    return {
        "display_name": display_name,
        "handle": handle,
        "tagline": "opulence",
        "following": 2,
        "followers": 0,
        "avatar_url": user.gravatar(size=200),
    }

@login_required
def profile(request):
    profile_username = request.GET.get("user")
    if profile_username:
        try:
            profile_user = user_repo.get_by_username(profile_username)
        except User.DoesNotExist:
            raise Http404("User not found")
    else:
        profile_user = request.user

    profile_data = _profile_data_for_user(profile_user)

    if request.method == "POST":
        if profile_user != request.user:
            return redirect("profile")
        form = UserForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.add_message(request, messages.SUCCESS, "Profile updated!")
            return redirect("profile")
    else:
        if profile_user == request.user:
            form = UserForm(instance=request.user)
        else:
            form = None

    posts = post_repo.list_for_user(
        profile_user.id,
        order_by=("-created_at",),
    )

    return render(
        request,
        "profile.html",
        {
            "profile": profile_data,
            "collections": PROFILE_COLLECTIONS,
            "form": form,
            "profile_user": profile_user,
            "is_own_profile": profile_user == request.user,
            "posts": posts,
        },
    )

@login_required
def collection_detail(request, slug):
    collection = next((c for c in PROFILE_COLLECTIONS if c["slug"] == slug), None)
    if not collection:
        raise Http404()

    context = {
        "profile": _profile_data_for_user(request.user),
        "collection": collection,
    }
    return render(request, "collection_detail.html", context)

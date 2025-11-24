from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from recipes.forms import UserForm

# Mocked collections to let the profile page feel populated before
# collections and saved posts exist in the database.
COMMON_COLLECTION_ITEMS = [
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80",  # pizza with basil
    "https://images.unsplash.com/photo-1482049016688-2d3e1b311543?auto=format&fit=crop&w=1200&q=80",  # smoothie bowls
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80",  # pizza repeat for mood board consistency
    "https://images.unsplash.com/photo-1490645935967-10de6ba17061?auto=format&fit=crop&w=1200&q=80",  # brunch spread
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80",  # pizza slice closeup
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80",  # rustic pizza board
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80",  # basil pizza overhead
    "https://images.unsplash.com/photo-1481931715705-36fdd4e1bf4d?auto=format&fit=crop&w=1200&q=80",  # tacos lineup
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80",  # pizza on wooden board
]

TRAVERSE_ITEMS = [
    "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?auto=format&fit=crop&w=1200&q=80",  # ramen bowl
    "https://images.unsplash.com/photo-1512058564366-18510be2db19?auto=format&fit=crop&w=1200&q=80",  # dim sum spread
    "https://images.unsplash.com/photo-1481391032119-d89fee407e44?auto=format&fit=crop&w=1200&q=80",  # gelato cones
    "https://images.unsplash.com/photo-1521017432531-fbd92d768814?auto=format&fit=crop&w=1200&q=80",  # sushi assortment
    "https://images.unsplash.com/photo-1473093295043-cdd812d0e601?auto=format&fit=crop&w=1200&q=80",  # grilled steak
    "https://images.unsplash.com/photo-1490645935967-10de6ba17061?auto=format&fit=crop&w=1200&q=80",  # brunch board
    "https://images.unsplash.com/photo-1481931715705-36fdd4e1bf4d?auto=format&fit=crop&w=1200&q=80",  # tacos line
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80",  # pizza hero
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80",  # pizza hero 2
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
        "cover": "https://images.unsplash.com/photo-1478144592103-25e218a04891?auto=format&fit=crop&w=1200&q=80",  # pasta bowl
        "items": COMMON_COLLECTION_ITEMS,
    },
    {
        "slug": "baking-basics",
        "title": "Baking Basics",
        "count": 41,
        "cover": "https://images.unsplash.com/photo-1467003909585-2f8a72700288?auto=format&fit=crop&w=1200&q=80",  # cookies cooling rack
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
        "cover": "https://images.unsplash.com/photo-1478145046317-39f10e56b5e9?auto=format&fit=crop&w=1200&q=80",  # veggie sandwich
        "items": COMMON_COLLECTION_ITEMS,
    },
    {
        "slug": "sweet-tooth",
        "title": "Sweet Tooth",
        "count": 2,
        "cover": "https://images.unsplash.com/photo-1505253758473-96b7015fcd40?auto=format&fit=crop&w=1200&q=80",  # stack of pancakes
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
    """Return profile meta blended with the current user."""

    fallback_handle = "@anmzn"
    handle = user.username or fallback_handle
    # Temporary display name users can customize later.
    display_name = "ayancooks"
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
    """
    Show the Cosmos-style profile with collections and an edit modal.

    The page is currently powered by mocked collections so designers can
    navigate a full experience before backend data is wired in.
    """

    profile_data = _profile_data_for_user(request.user)
    if request.method == "POST":
        form = UserForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.add_message(request, messages.SUCCESS, "Profile updated!")
            return redirect("profile")
    else:
        form = UserForm(instance=request.user)

    return render(
        request,
        "profile.html",
        {
            "profile": profile_data,
            "collections": PROFILE_COLLECTIONS,
            "form": form,
        },
    )


@login_required
def collection_detail(request, slug):
    """Display a single collection and its saved items."""

    collection = next((c for c in PROFILE_COLLECTIONS if c["slug"] == slug), None)
    if not collection:
        raise Http404()

    context = {
        "profile": _profile_data_for_user(request.user),
        "collection": collection,
    }
    return render(request, "collection_detail.html", context)

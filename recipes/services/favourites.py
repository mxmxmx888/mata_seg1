"""Service helpers for favourite collections."""

from django.http import Http404
from django.shortcuts import get_object_or_404
from recipes.models import Favourite, FavouriteItem


class FavouriteService:
    """Encapsulate collection fetching and mutation."""

    def __init__(self, favourite_model=Favourite, favourite_item_model=FavouriteItem):
        self.favourite_model = favourite_model
        self.favourite_item_model = favourite_item_model

    def list_for_user(self, user):
        """Return all favourites for a user with prefetched items/posts."""
        return self.favourite_model.objects.filter(user=user).prefetch_related("items__recipe_post")

    def fetch_for_user(self, slug, user):
        """Fetch a favourite by id and user or raise 404."""
        return get_object_or_404(self.favourite_model, id=slug, user=user)

    def delete(self, favourite):
        """Delete a favourite collection."""
        favourite.delete()

    def update_name(self, favourite, name):
        """Update favourite name and persist."""
        favourite.name = name
        favourite.save(update_fields=["name"])
        return favourite

    def posts_for(self, favourite):
        """Return recipe posts for a favourite."""
        items_qs = self.favourite_item_model.objects.filter(favourite=favourite).select_related("recipe_post")
        if hasattr(items_qs, "order_by"):
            items_qs = items_qs.order_by("-added_at", "-id")
        return [item.recipe_post for item in items_qs if item.recipe_post]

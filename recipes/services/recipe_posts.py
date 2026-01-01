"""Service helpers for recipe post creation, updates, and engagement."""

from django.shortcuts import get_object_or_404
from django.utils import timezone

from recipes.models import Favourite, Ingredient, Like, RecipePost
from recipes.models.favourite_item import FavouriteItem


class RecipePostService:
    """Encapsulate recipe post lifecycle and engagement operations."""

    def create_from_form(self, form, user):
        """Create and return a recipe post from a validated form."""
        cleaned = form.cleaned_data
        tags_list = form.parse_tags()
        return RecipePost.objects.create(
            author=user,
            title=cleaned["title"],
            description=cleaned.get("description") or "",
            prep_time_min=cleaned.get("prep_time_min") or 0,
            cook_time_min=cleaned.get("cook_time_min") or 0,
            serves=cleaned.get("serves") or 0,
            nutrition=cleaned.get("nutrition") or "",
            tags=tags_list,
            category=cleaned.get("category") or "",
            visibility=cleaned.get("visibility") or RecipePost.VISIBILITY_PUBLIC,
            published_at=timezone.now(),
        )

    def update_from_form(self, recipe, form):
        """Update an existing recipe from a validated form."""
        cleaned = form.cleaned_data
        recipe.title = cleaned["title"]
        recipe.description = cleaned.get("description") or ""
        recipe.prep_time_min = cleaned.get("prep_time_min") or 0
        recipe.cook_time_min = cleaned.get("cook_time_min") or 0
        recipe.serves = cleaned.get("serves") or 0
        recipe.nutrition = cleaned.get("nutrition") or ""
        recipe.tags = form.parse_tags()
        recipe.category = cleaned.get("category") or ""
        recipe.visibility = cleaned.get("visibility") or RecipePost.VISIBILITY_PUBLIC
        recipe.save()
        return recipe

    def persist_relations(self, form, recipe):
        """Persist form-related relations and ensure primary image is set."""
        form.create_ingredients(recipe)
        form.create_steps(recipe)
        form.create_images(recipe)
        self.set_primary_image(recipe)

    def shopping_items_for(self, recipe):
        """Return shopping item data for the recipe edit form."""
        return [
            {
                "name": ing.name,
                "url": ing.shop_url or "",
                "image_url": ing.shop_image_upload.url if ing.shop_image_upload else "",
            }
            for ing in Ingredient.objects.filter(recipe_post=recipe, shop_url__isnull=False).order_by("position")
        ]

    def resolve_collection(self, user, *, collection_id=None, collection_name=None):
        """Find or create a Favourite collection for a user."""
        if collection_id:
            favourite = get_object_or_404(Favourite, id=collection_id, user=user)
            return favourite, False

        name = (collection_name or "favourites").strip() or "favourites"
        favourite, created_collection = Favourite.objects.get_or_create(
            user=user,
            name=name,
        )
        return favourite, created_collection

    def toggle_save(self, favourite, recipe):
        """Toggle save state for a recipe within a Favourite; return (is_saved_now, new_count)."""
        existing = FavouriteItem.objects.filter(
            favourite=favourite,
            recipe_post=recipe,
        )

        if existing.exists():
            existing.delete()
            new_count = max(0, (recipe.saved_count or 0) - 1)
            return False, new_count

        FavouriteItem.objects.create(
            favourite=favourite,
            recipe_post=recipe,
        )
        new_count = (recipe.saved_count or 0) + 1
        return True, new_count

    def collection_thumb(self, cover_post, fallback_post):
        """Choose a thumbnail URL for a collection using cover or fallback posts."""
        thumb_url = getattr(cover_post, "primary_image_url", None) or getattr(cover_post, "image", None)
        if not thumb_url and fallback_post:
            thumb_url = getattr(fallback_post, "primary_image_url", None) or getattr(fallback_post, "image", None)
        return thumb_url or "https://placehold.co/1200x800/0f0f14/ffffff?text=Collection"

    def toggle_favourite(self, user, recipe, *, collection_id=None, collection_name=None):
        """Toggle save/unsave for a recipe and return details."""
        favourite, created_collection = self.resolve_collection(
            user,
            collection_id=collection_id,
            collection_name=collection_name,
        )
        is_saved_now, new_count = self.toggle_save(favourite, recipe)
        RecipePost.objects.filter(id=recipe.id).update(saved_count=new_count)
        collection = {
            "id": str(favourite.id),
            "name": favourite.name,
            "created": created_collection,
            "thumb_url": self.collection_thumb(favourite.cover_post, recipe),
        }
        return is_saved_now, new_count, collection

    def toggle_like(self, user, recipe):
        """Toggle like/unlike for a recipe."""
        existing = Like.objects.filter(user=user, recipe_post=recipe)
        if existing.exists():
            existing.delete()
            return False
        Like.objects.create(user=user, recipe_post=recipe)
        return True

    def set_primary_image(self, recipe):
        """Persist the first RecipeImage URL onto the legacy image field for display."""
        primary_image = recipe.images.first()
        if primary_image and primary_image.image:
            recipe.image = primary_image.image.url
            recipe.save(update_fields=["image"])

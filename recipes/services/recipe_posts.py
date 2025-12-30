"""Service helpers for recipe post creation, updates, and engagement."""

from django.utils import timezone

from recipes.models import Ingredient, Like, RecipePost
from recipes.views.recipe_view_helpers import (
    collection_thumb,
    resolve_collection,
    set_primary_image,
    toggle_save,
)


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
        set_primary_image(recipe)

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

    def toggle_favourite(self, request, recipe):
        """Toggle save/unsave for a recipe and return details."""
        favourite, created_collection = resolve_collection(request, recipe)
        is_saved_now, new_count = toggle_save(favourite, recipe)
        RecipePost.objects.filter(id=recipe.id).update(saved_count=new_count)
        collection = {
            "id": str(favourite.id),
            "name": favourite.name,
            "created": created_collection,
            "thumb_url": collection_thumb(favourite.cover_post, recipe),
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

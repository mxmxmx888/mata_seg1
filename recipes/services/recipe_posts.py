"""Service helpers for recipe post creation, updates, and engagement."""

from django.shortcuts import get_object_or_404
from django.utils import timezone

from recipes.models import Favourite, Ingredient, Like, RecipePost
from recipes.models.favourite_item import FavouriteItem
from recipes.models.followers import Follower
from recipes.models.recipe_step import RecipeStep


class RecipePostService:
    """Encapsulate recipe post lifecycle and engagement operations."""

    def fetch_post(self, post_id):
        """Fetch a recipe post by id or raise 404."""
        return get_object_or_404(RecipePost, id=post_id)

    def fetch_owned_post(self, user, post_id):
        """Fetch a recipe post owned by the given user or raise 404."""
        return get_object_or_404(RecipePost, id=post_id, author=user)

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

    # --- view support helpers -------------------------------------------
    def comments_page(self, recipe, request, page_size=50):
        """Return a slice of comments for a recipe along with pagination metadata."""
        comments_qs = recipe.comments.select_related("user").order_by("-created_at")
        try:
            page_number = max(1, int(request.GET.get("comments_page") or 1))
        except (TypeError, ValueError):
            page_number = 1
        start = (page_number - 1) * page_size
        end = start + page_size
        comments_page = list(comments_qs[start:end])
        has_more_comments = comments_qs.count() > end
        return comments_page, has_more_comments, page_number

    def saved_posts_for_user(self, user):
        """List all unique recipes saved by the given user (most recent first)."""
        favourite_items = (
            FavouriteItem.objects.filter(favourite__user=user)
            .select_related("recipe_post")
            .order_by("-added_at")
        )

        seen_ids = set()
        posts = []
        for item in favourite_items:
            post = self._valid_saved_post(item, seen_ids)
            if not post:
                continue
            posts.append(post)
        return posts

    # --- query helpers moved from view layer for cohesion -----------------
    def user_reactions(self, request_user, recipe):
        """Return flags and counts for likes/saves and following for the current user."""
        user_liked = Like.objects.filter(user=request_user, recipe_post=recipe).exists()
        user_saved = FavouriteItem.objects.filter(
            favourite__user=request_user,
            recipe_post=recipe,
        ).exists()
        is_following_author = Follower.objects.filter(
            follower=request_user,
            author=recipe.author,
        ).exists()
        likes_count = Like.objects.filter(recipe_post=recipe).count()
        saves_count = FavouriteItem.objects.filter(recipe_post=recipe).count()
        return {
            "user_liked": user_liked,
            "user_saved": user_saved,
            "is_following_author": is_following_author,
            "likes_count": likes_count,
            "saves_count": saves_count,
        }

    def ingredient_lists(self, recipe):
        """Split ingredients into non-shop list and shop-linked list."""
        ingredients_all = list(Ingredient.objects.filter(recipe_post=recipe).order_by("position"))
        shop_ingredients = [
            ing for ing in ingredients_all if getattr(ing, "shop_url", None) and str(ing.shop_url).strip()
        ]
        non_shop_ingredients = [ing for ing in ingredients_all if ing not in shop_ingredients]
        return non_shop_ingredients, shop_ingredients

    def recipe_steps(self, recipe):
        """Return ordered step descriptions for a recipe."""
        steps_qs = RecipeStep.objects.filter(recipe_post=recipe).order_by("position")
        return [s.description for s in steps_qs]

    def collections_modal_state(self, user, recipe):
        """Build modal-friendly collection metadata for a user and target recipe."""
        collections = [self._collection_entry(fav, recipe) for fav in self._favourites_for(user)]
        collections.sort(key=lambda c: c.get("last_saved_at") or c.get("created_at"), reverse=True)
        collections.sort(key=lambda c: 0 if c.get("saved") else 1)
        return collections

    def _favourites_for(self, user):
        """Return all Favourite collections for a user with prefetched items and cover posts."""
        return Favourite.objects.filter(user=user).prefetch_related("items__recipe_post", "cover_post")

    def _collection_entry(self, fav, recipe):
        """Build a dictionary entry representing a collection's state relative to a recipe."""
        items = list(fav.items.all())
        saved_here = any(item.recipe_post_id == recipe.id for item in items)
        cover_post = fav.cover_post or self._first_item_post(items)
        fallback_cover = recipe if saved_here else self._first_item_post(items)
        return {
            "id": str(fav.id),
            "name": fav.name,
            "saved": saved_here,
            "count": len(items),
            "thumb_url": self.collection_thumb(cover_post, fallback_cover),
            "last_saved_at": self._last_saved_at(items, fav.created_at),
            "created_at": fav.created_at,
        }

    def _first_item_post(self, items):
        """Return the first recipe post found in a list of FavouriteItems, or None."""
        for item in items:
            if item.recipe_post:
                return item.recipe_post
        return None

    def _last_saved_at(self, items, default):
        """Find the most recent added_at timestamp from items, or return default."""
        latest = default
        for item in items:
            latest = self._maybe_update_latest(latest, getattr(item, "added_at", None))
        return latest

    def _valid_saved_post(self, item, seen_ids):
        post = getattr(item, "recipe_post", None)
        if not post or post.id in seen_ids:
            return None
        seen_ids.add(post.id)
        return post

    def _maybe_update_latest(self, current, added_at):
        if not added_at:
            return current
        if current is None or added_at > current:
            return added_at
        return current

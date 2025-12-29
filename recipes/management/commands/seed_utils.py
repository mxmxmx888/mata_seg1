"""Helper utilities for assembling seed data objects without hitting the DB too often."""

import os
from random import sample, randint, choice
from typing import Any, Dict, List, Set, Tuple

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from recipes.models.favourite import Favourite
from recipes.models.favourite_item import FavouriteItem
from recipes.models.ingredient import Ingredient
from recipes.models.recipe_post import RecipePost, RecipeImage
from recipes.models.recipe_step import RecipeStep
from .seed_data import (
    BASE_INGREDIENT_POOL,
    SHOP_ITEM_OVERRIDES,
    SHOP_IMAGE_MAP,
    shop_image_file_pool,
    tags_pool,
    categories,
)


class SeedHelpers:
    """Non-DB helpers that create model instances for bulk seeding."""

    def _make_uploaded_image(self, rel_path: str) -> SimpleUploadedFile:
        """Wrap a real image file into a Django SimpleUploadedFile."""
        abs_path = os.path.join(settings.BASE_DIR, rel_path.lstrip("/"))
        with open(abs_path, "rb") as f:
            return SimpleUploadedFile(
                name=os.path.basename(abs_path),
                content=f.read(),
                content_type="image/jpeg",
            )

    def _safe_uploaded_image(self, rel_path: str) -> SimpleUploadedFile | None:
        """Return an uploaded image or None when the file is missing."""
        try:
            return self._make_uploaded_image(rel_path)
        except FileNotFoundError:
            return None

    def _build_recipe_post(self, author_id: str, image_pool: list[str]) -> RecipePost:
        """Construct an unsaved RecipePost with randomized fields."""
        title = self.faker.sentence(nb_words=5).rstrip(".")[:255]
        description = self.faker.paragraph(nb_sentences=3)[:4000]
        tags = list(set(sample(tags_pool, randint(0, min(4, len(tags_pool))))))
        return RecipePost(
            author_id=author_id,
            title=title,
            description=description,
            image=choice(image_pool),
            prep_time_min=randint(0, 60),
            cook_time_min=randint(0, 90),
            serves=0 if randint(1, 4) == 1 else choice([2, 4, 6, 8]),
            tags=tags,
            nutrition=f"kcal={randint(250, 800)}; protein={randint(5, 40)}g",
            category=choice(categories),
            saved_count=0,
            published_at=timezone.now(),
        )

    def _build_recipe_images(self, post: RecipePost, image_pool: list[str]) -> List[RecipeImage]:
        """Build unsaved RecipeImage objects for a given post."""
        images: List[RecipeImage] = []
        img_count = randint(2, 4)
        chosen = sample(image_pool, k=min(img_count, len(image_pool)))
        for position, rel_path in enumerate(chosen):
            uploaded = self._safe_uploaded_image(rel_path)
            if not uploaded:
                continue
            images.append(
                RecipeImage(
                    recipe_post_id=post.id,
                    image=uploaded,
                    position=position,
                )
            )
        return images

    def _build_posts_for_author(
        self, author_id: str, per_user: int, image_pool: list[str]
    ) -> Tuple[List[RecipePost], List[RecipeImage]]:
        """Create posts plus their images for a given author."""
        posts: List[RecipePost] = []
        images: List[RecipeImage] = []
        count = randint(1, max(1, per_user))
        for _ in range(count):
            post = self._build_recipe_post(author_id, image_pool)
            posts.append(post)
            images.extend(self._build_recipe_images(post, image_pool))
        return posts, images

    def _build_ingredients_for_post(
        self, post_id: str, ingredient_set: List[Dict[str, Any]]
    ) -> List[Ingredient]:
        """Build Ingredient rows for a post with plain ingredients plus shop items."""
        rows: List[Ingredient] = []
        seen_names: set[str] = set()
        position = self._add_base_ingredients(rows, seen_names, post_id)
        self._add_shop_ingredients(rows, seen_names, position, post_id, ingredient_set)
        return rows

    def _add_base_ingredients(self, rows, seen_names, post_id):
        position = 1
        base_pool = BASE_INGREDIENT_POOL or []
        base_count = randint(5, 8)
        base_choices = sample(base_pool, k=min(base_count, len(base_pool))) if base_pool else []
        for name in base_choices:
            position = self._append_ingredient(rows, seen_names, post_id, name, position)
        return position

    def _add_shop_ingredients(self, rows, seen_names, position, post_id, ingredient_set):
        for item in ingredient_set:
            name = item["name"]
            if name.lower() in seen_names:
                continue
            image_file, shop_url = self._resolve_ingredient_assets(item, name.lower())
            position = self._append_ingredient(
                rows,
                seen_names,
                post_id,
                name,
                position,
                shop_url=shop_url,
                shop_image_upload=image_file,
            )

    def _append_ingredient(self, rows, seen_names, post_id, name, position, **extra_fields):
        rows.append(
            Ingredient(
                recipe_post_id=post_id,
                name=name,
                position=position,
                **extra_fields,
            )
        )
        seen_names.add(name.lower())
        return position + 1

    def _resolve_ingredient_assets(
        self, item: Dict[str, Any], name_key: str
    ) -> Tuple[SimpleUploadedFile | None, str | None]:
        """Resolve shopping URL and image file for an ingredient (with overrides)."""
        override = SHOP_ITEM_OVERRIDES.get(name_key, {})
        shop_url = override.get("shop_url") or item.get("shop_url")
        rel_path = override.get("shop_image") or item.get("shop_image") or SHOP_IMAGE_MAP.get(name_key)
        image_file = self._safe_uploaded_image(rel_path) if rel_path else None
        if not image_file and shop_image_file_pool:
            image_file = self._safe_uploaded_image(choice(shop_image_file_pool))
        return image_file, shop_url

    def _build_favourites(self, user_ids: List[str], per_user: int, favourite_names: list[str]) -> List[Favourite]:
        """Create unsaved Favourite rows for each user from provided names."""
        collections_per_user = min(per_user, len(favourite_names))
        fav_keys: Set[Tuple[str, str]] = set()
        favourites: List[Favourite] = []
        for user_id in user_ids:
            favourites.extend(self._favourites_for_user(user_id, collections_per_user, favourite_names, fav_keys))
        return favourites

    def _favourites_for_user(self, user_id, collections_per_user, favourite_names, fav_keys):
        favourites: List[Favourite] = []
        for name in sample(favourite_names, k=collections_per_user):
            key = (str(user_id), name)
            if key in fav_keys:
                continue
            fav_keys.add(key)
            favourites.append(Favourite(user_id=user_id, name=name))
        return favourites

    def _fetch_favourites_by_user(self, user_ids: List[str]) -> Dict[str, List[str]]:
        """Return mapping of user_id to list of favourite IDs."""
        favourites = list(
            Favourite.objects.filter(user_id__in=user_ids).values_list("id", "user_id")
        )
        favs_by_user: Dict[str, List[str]] = {}
        for fav_id, u_id in favourites:
            favs_by_user.setdefault(str(u_id), []).append(str(fav_id))
        return favs_by_user

    def _build_favourite_items(
        self,
        user_ids: List[str],
        posts: List[str],
        favs_by_user: Dict[str, List[str]],
    ) -> List[FavouriteItem]:
        """Build FavouriteItem rows for sampled posts per user favourite."""
        items: List[FavouriteItem] = []
        for user_id in user_ids:
            items.extend(self._items_for_user(user_id, posts, favs_by_user))
        return items

    def _items_for_user(self, user_id, posts, favs_by_user):
        items: List[FavouriteItem] = []
        for fav_id in favs_by_user.get(str(user_id), []):
            k = randint(3, 8)
            for post_id in sample(posts, k=min(k, len(posts))):
                items.append(FavouriteItem(favourite_id=fav_id, recipe_post_id=post_id))
        return items


def create_username(first_name, last_name):
    """Build a simple lowercase username from a name."""
    return '@' + first_name.lower() + last_name.lower()


def create_email(first_name, last_name):
    """Build a deterministic email for seeded users."""
    return first_name + '.' + last_name + '@example.org'

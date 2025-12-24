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
from .seed_data import SHOP_ITEM_OVERRIDES, SHOP_IMAGE_MAP, shop_image_file_pool, tags_pool, categories


class SeedHelpers:
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
        try:
            return self._make_uploaded_image(rel_path)
        except FileNotFoundError:
            return None

    def _build_recipe_post(self, author_id: str, image_pool: list[str]) -> RecipePost:
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
            nutrition=f\"kcal={randint(250, 800)}; protein={randint(5, 40)}g\",
            category=choice(categories),
            saved_count=0,
            published_at=timezone.now(),
        )

    def _build_recipe_images(self, post: RecipePost, image_pool: list[str]) -> List[RecipeImage]:
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
        rows: List[Ingredient] = []
        position = 1
        for item in ingredient_set:
            name = item["name"]
            image_file, shop_url = self._resolve_ingredient_assets(item, name.lower())
            rows.append(
                Ingredient(
                    recipe_post_id=post_id,
                    name=name,
                    position=position,
                    shop_url=shop_url,
                    shop_image_upload=image_file,
                )
            )
            position += 1
        return rows

    def _resolve_ingredient_assets(
        self, item: Dict[str, Any], name_key: str
    ) -> Tuple[SimpleUploadedFile | None, str | None]:
        override = SHOP_ITEM_OVERRIDES.get(name_key, {})
        shop_url = override.get("shop_url") or item.get("shop_url")
        rel_path = override.get("shop_image") or item.get("shop_image") or SHOP_IMAGE_MAP.get(name_key)
        image_file = self._safe_uploaded_image(rel_path) if rel_path else None
        if not image_file and shop_image_file_pool:
            image_file = self._safe_uploaded_image(choice(shop_image_file_pool))
        return image_file, shop_url

    def _build_favourites(self, user_ids: List[str], per_user: int, favourite_names: list[str]) -> List[Favourite]:
        collections_per_user = min(per_user, len(favourite_names))
        favourites: List[Favourite] = []
        fav_keys: Set[Tuple[str, str]] = set()
        for user_id in user_ids:
            chosen = sample(favourite_names, k=collections_per_user)
            for name in chosen:
                key = (str(user_id), name)
                if key in fav_keys:
                    continue
                fav_keys.add(key)
                favourites.append(Favourite(user_id=user_id, name=name))
        return favourites

    def _fetch_favourites_by_user(self, user_ids: List[str]) -> Dict[str, List[str]]:
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
        items: List[FavouriteItem] = []
        for user_id in user_ids:
            user_fav_ids = favs_by_user.get(str(user_id), [])
            if not user_fav_ids:
                continue
            for fav_id in user_fav_ids:
                k = randint(3, 8)
                chosen_posts = sample(posts, k=min(k, len(posts)))
                for post_id in chosen_posts:
                    items.append(FavouriteItem(favourite_id=fav_id, recipe_post_id=post_id))
        return items


def create_username(first_name, last_name):
    return '@' + first_name.lower() + last_name.lower()


def create_email(first_name, last_name):
    return first_name + '.' + last_name + '@example.org'

"""Service helpers for shoppable ingredient items."""

import hashlib
from django.core.paginator import Paginator
from django.db.models import Q
from recipes.models import Ingredient, RecipePost
from recipes.services import PrivacyService


class ShopService:
    """Encapsulate visibility, shuffling, and pagination of shop items."""

    def __init__(self, privacy_service=None):
        self.privacy_service = privacy_service or PrivacyService()

    def visible_items(self, user):
        """Return Ingredient queryset limited to items with shop links visible to the user."""
        items_qs = Ingredient.objects.filter(
            Q(shop_url__isnull=False) & ~Q(shop_url__regex=r'^\s*$')
        ).select_related("recipe_post")

        visible_posts = self.privacy_service.filter_visible_posts(
            RecipePost.objects.filter(
                id__in=items_qs.values_list("recipe_post_id", flat=True).distinct()
            ),
            user,
        ).values_list("id", flat=True)

        return items_qs.filter(recipe_post_id__in=visible_posts)

    def paginated_shuffled_items(self, user, seed, page_number):
        """Shuffle shop items deterministically by seed and return the paginated page."""
        items_qs = self.visible_items(user)
        item_ids = list(items_qs.values_list("id", flat=True))
        shuffled_ids = sorted(
            item_ids, key=lambda pk: hashlib.sha256(f"{seed}-{pk}".encode("utf-8")).hexdigest()
        )

        paginator = Paginator(shuffled_ids, 24)
        page_obj = paginator.get_page(page_number or 1)

        current_ids = list(page_obj.object_list)
        if not current_ids:  # pragma: no cover - empty page fallback
            page_obj.object_list = []
            return page_obj

        id_positions = {pk: idx for idx, pk in enumerate(current_ids)}
        current_items = sorted(
            items_qs.filter(id__in=current_ids),
            key=lambda obj: id_positions.get(obj.id, 0),
        )
        page_obj.object_list = current_items
        return page_obj

    def search_items_page(self, user, query, page_number, page_size=24):
        """Return paginated, filtered shop items visible to the user."""
        qs = self.visible_items(user).order_by("-id")
        if query:
            qs = qs.filter(Q(name__icontains=query)).distinct()
        paginator = Paginator(qs, page_size)
        return paginator.get_page(page_number)

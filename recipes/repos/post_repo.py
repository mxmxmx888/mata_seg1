"""Repository helpers for fetching recipe posts."""

from typing import Any, Dict, List, Optional, Sequence
from django.db.models import QuerySet
from recipes.db_accessor import DB_Accessor
from recipes.models.recipe_post import RecipePost
from recipes.models import Follows


class PostRepo(DB_Accessor):
    """Repository for RecipePost queries (feed, user-specific, following)."""
    def __init__(self) -> None:
        """Initialise with the RecipePost model."""
        super().__init__(RecipePost)

    def list_ids(self) -> List[str]:
        """Return all recipe post IDs."""
        return list(self.model.objects.values_list("id", flat=True))

    def list_for_feed(
        self,
        *,
        category: Optional[str] = None,
        author_id: Optional[int] = None,
        order_by: Sequence[str] = ("created_at",),
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> QuerySet:
        """Return posts for feed with optional filters and paging."""
        filters: Dict[str, Any] = {}

        if category and category.lower() != "all":
            
            filters["category__iexact"] = category

        if author_id is not None:
            filters["author_id"] = author_id

        return self.list(
            filters=filters or None,
            order_by=order_by,
            limit=limit,
            offset=offset,
            as_dict=False,
        )

    def list_for_user(
        self,
        user_id: int,
        *,
        order_by: Sequence[str] = ("created_at",),
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> QuerySet:
        """Return posts authored by a given user."""
        return self.list_for_feed(
            author_id=user_id,
            order_by=order_by,
            limit=limit,
            offset=offset,
        )
    
    def list_for_following(self, user_id, limit=50):
        """Return recent posts from authors the user follows."""
        followee_ids = (
            Follows.objects
            .filter(author_id=user_id)
            .values_list("followee_id", flat=True)
        )

        if not followee_ids:
            model_cls = getattr(self, "model", RecipePost)
            return model_cls.objects.none()

        if hasattr(self, "list_for_feed"):
            qs = self.list_for_feed()
        elif hasattr(self, "list_all"):
            qs = self.list_all()
        else:
            model_cls = getattr(self, "model", RecipePost)
            qs = model_cls.objects.all()

        return qs.filter(author_id__in=followee_ids).order_by("-created_at")[:limit]

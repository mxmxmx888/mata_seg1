"""Repository helpers for follower relationships."""

from typing import Any, Dict, List, Optional
from recipes.db_accessor import DB_Accessor
from recipes.models.followers import Follower  # adjust import to your app


class FollowersRepo(DB_Accessor):
    """Repository wrapper for follower relationships."""
    def __init__(self) -> None:
        """Initialise with the Follower model."""
        super().__init__(Follower)

    def list_followers(self, *, author_id: str, limit: int = 20, offset: int = 0, as_dict: bool = True) -> List[Dict[str, Any]]:
        """List followers of an author with optional paging."""
        return self.list(filters={"author_id": author_id}, order_by=("follower_id",), limit=limit, offset=offset, as_dict=as_dict)  # type: ignore[return-value]

    def is_following(self, *, follower_id: str, author_id: str) -> bool:
        """Return True if follower_id follows author_id."""
        return Follower.objects.filter(follower_id=follower_id, author_id=author_id).exists()

    def follow(self, *, follower_id: str, author_id: str) -> Follower:
        """Create a follower relation."""
        return self.create(follower_id=follower_id, author_id=author_id)

    def unfollow(self, *, follower_id: str, author_id: str) -> int:
        """Remove a follower relation."""
        return self.delete(follower_id=follower_id, author_id=author_id)

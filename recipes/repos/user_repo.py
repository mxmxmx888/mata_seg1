"""Repository helpers for user lookups."""

from typing import List

from recipes.db_accessor import DB_Accessor
from recipes.models.user import User


class UserRepo(DB_Accessor):
    """Repository for basic user queries."""
    def __init__(self) -> None:
        """Initialise with the User model."""
        super().__init__(User)

    def list_ids(self) -> List[int]:
        """Return all user IDs."""
        return list(self.model.objects.values_list("id", flat=True))

    def get_by_id(self, user_id: int) -> User:
        """Return a user by id."""
        return self.get(id=user_id)

    def get_by_username(self, username: str) -> User:
        """Return a user by username."""
        return self.get(username=username)

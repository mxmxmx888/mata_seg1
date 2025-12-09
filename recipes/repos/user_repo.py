from typing import List

from recipes.db_accessor import DB_Accessor
from recipes.models.user import User


class UserRepo(DB_Accessor):
    def __init__(self) -> None:
        super().__init__(User)

    def list_ids(self) -> List[int]:
        return list(self.model.objects.values_list("id", flat=True))

    def get_by_id(self, user_id: int) -> User:
        return self.get(id=user_id)

    def get_by_username(self, username: str) -> User:
        return self.get(username=username)

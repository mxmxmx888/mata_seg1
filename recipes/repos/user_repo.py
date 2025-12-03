from typing import List
from recipes.db_accessor import DB_Accessor
from recipes.models.user import User


class UserRepo(DB_Accessor):
    def __init__(self) -> None:
        super().__init__(User)

    def list_ids(self) -> List[str]:
        return list(self.model.objects.values_list("id", flat=True))
from typing import Any, Dict, List, Mapping, Optional, Sequence, Type
from django.db.models import Model, QuerySet


class DB_Accessor:

    def __init__(self, model: Type[Model]) -> None:
        self.model = model

    def list(
        self,
        *,
        filters: Optional[Mapping[str, Any]] = None,
        order_by: Sequence[str] = (),
        limit: Optional[int] = None,
        offset: int = 0,
        as_dict: bool = False,
    ) -> QuerySet | List[Dict[str, Any]]:
        qs: QuerySet = self.model.objects.filter(**(filters or {}))
        if order_by:
            qs = qs.order_by(*order_by)
        qs = qs[offset:] if limit is None else qs[offset : offset + max(0, int(limit))]
        return list(qs.values()) if as_dict else qs

    def get(self, **lookup: Any) -> Model:
        return self.model.objects.get(**lookup)

    def create(self, **data: Any) -> Model:
        return self.model.objects.create(**data)

    def update(self, lookup: Mapping[str, Any], **data: Any) -> int:
        return self.model.objects.filter(**lookup).update(**data)

    def delete(self, **lookup: Any) -> int:
        count, _ = self.model.objects.filter(**lookup).delete()
        return count
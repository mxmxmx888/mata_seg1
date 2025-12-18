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

        # SQLite cannot UNION subqueries that include LIMIT/OFFSET.
        # To keep union-able querysets, slice to objects first, then refetch
        # without ORDER BY / LIMIT while preserving the cached order.
        needs_slice = offset or limit is not None
        if needs_slice:
            start = max(0, int(offset))
            end = None if limit is None else start + max(0, int(limit))
            objects = list(qs[start:end])
            model_cls = getattr(self, "model", None) or self.model
            if not objects:
                qs = model_cls.objects.none()
            else:
                ids = [obj.pk for obj in objects]
                qs = model_cls.objects.filter(pk__in=ids).order_by()
                qs._result_cache = objects  # preserve original slice ordering
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

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
        qs = self._apply_ordering(qs, order_by)
        qs = self._apply_slice(qs, offset=offset, limit=limit)
        return list(qs.values()) if as_dict else qs

    def _apply_ordering(self, qs: QuerySet, order_by: Sequence[str]) -> QuerySet:
        return qs.order_by(*order_by) if order_by else qs

    def _apply_slice(
        self, qs: QuerySet, *, offset: int = 0, limit: Optional[int] = None
    ) -> QuerySet:

        if not (offset or limit is not None):
            return qs
        start = max(0, int(offset))
        end = None if limit is None else start + max(0, int(limit))
        objects = list(qs[start:end])
        model_cls = getattr(self, "model", None) or self.model
        if not objects:
            return model_cls.objects.none()
        ids = [obj.pk for obj in objects]
        qs = model_cls.objects.filter(pk__in=ids).order_by()
        qs._result_cache = objects  # preserve original slice ordering
        return qs

    def get(self, **lookup: Any) -> Model:
        return self.model.objects.get(**lookup)

    def create(self, **data: Any) -> Model:
        return self.model.objects.create(**data)

    def update(self, lookup: Mapping[str, Any], **data: Any) -> int:
        return self.model.objects.filter(**lookup).update(**data)

    def delete(self, **lookup: Any) -> int:
        count, _ = self.model.objects.filter(**lookup).delete()
        return count

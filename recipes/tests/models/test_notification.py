import uuid
from django.test import TestCase
from django.utils import timezone
from django.db import models

from recipes.tests.test_utils import make_user, make_recipe_post
from recipes.models.notification import Notification


class NotificationModelTestCase(TestCase):
    def setUp(self):
        self.user_a = make_user(username="@usera")
        self.user_b = make_user(username="@userb")
        self.post = make_recipe_post(author=self.user_a)

    def _build_notification_kwargs(self) -> dict:
        """
        Build kwargs for Notification.objects.create(...) by inspecting required fields.

        This avoids hardcoding your field names (except when we can safely infer
        how to create FK objects for User / RecipePost).
        """
        kwargs: dict = {}
        for field in Notification._meta.concrete_fields:
            if self._skip_field(field):
                continue
            if isinstance(field, models.ForeignKey):
                kwargs[field.name] = self._resolve_fk(field)
                continue
            kwargs[field.name] = self._resolve_field_value(field)
        return kwargs

    def _skip_field(self, field):
        if field.primary_key or getattr(field, "auto_created", False):
            return True
        if isinstance(field, models.DateTimeField) and (field.auto_now or field.auto_now_add):
            return True
        return field.has_default() or getattr(field, "null", False) or getattr(field, "blank", False)

    def _resolve_fk(self, field):
        rel_model = field.remote_field.model
        if rel_model._meta.label_lower.endswith("user"):
            return self.user_b
        if rel_model._meta.model_name == "recipepost":
            return self.post
        try:
            return rel_model.objects.create()
        except Exception:
            raise AssertionError(
                f"Notification has required FK '{field.name}' to '{rel_model.__name__}', "
                "but the test doesn't know how to create it. "
                f"Add a helper factory for {rel_model.__name__} and set it here."
            )

    def _resolve_field_value(self, field):
        if isinstance(field, (models.CharField, models.TextField)):
            return "Test notification"
        if isinstance(field, models.BooleanField):
            return False
        if isinstance(field, (models.IntegerField, models.BigIntegerField, models.SmallIntegerField)):
            return 1
        if isinstance(field, models.UUIDField):
            return uuid.uuid4()
        if isinstance(field, models.DateTimeField):
            return timezone.now()
        if isinstance(field, models.DateField):
            return timezone.now().date()
        if isinstance(field, models.TimeField):
            return timezone.now().time()
        raise AssertionError(
            f"Unhandled required field type for '{field.name}': {field.__class__.__name__}. "
            "Add handling in _build_notification_kwargs()."
        )

    def test_can_create_notification(self):
        n = Notification.objects.create(**self._build_notification_kwargs())
        self.assertIsNotNone(n.pk)

    def test_string_representation(self):
        n = Notification.objects.create(**self._build_notification_kwargs())
        s = str(n)
        self.assertTrue(isinstance(s, str))
        self.assertTrue(len(s) > 0)

    def test_default_is_read_is_false_if_field_exists(self):
        """
        Only checks if your model actually has an 'is_read' field.
        """
        field_names = {f.name for f in Notification._meta.concrete_fields}
        if "is_read" not in field_names:
            self.skipTest("Notification model has no is_read field")

        n = Notification.objects.create(**self._build_notification_kwargs())
        self.assertFalse(getattr(n, "is_read"))

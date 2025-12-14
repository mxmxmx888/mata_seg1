import uuid
from django.test import TestCase
from django.utils import timezone
from django.db import models

from recipes.tests.helpers import make_user, make_recipe_post
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
            # Skip PK / auto fields
            if field.primary_key or getattr(field, "auto_created", False):
                continue

            # Skip auto timestamps (auto_now / auto_now_add)
            if isinstance(field, models.DateTimeField) and (field.auto_now or field.auto_now_add):
                continue

            # If field has a default, let Django fill it
            if field.has_default():
                continue

            # If nullable / blankable, we can omit it
            # (blank is form-level, but usually aligns with "not required" semantics for seeding tests)
            if getattr(field, "null", False) or getattr(field, "blank", False):
                continue

            # Foreign keys
            if isinstance(field, models.ForeignKey):
                rel_model = field.remote_field.model

                # If FK points to User, choose one of our users
                if rel_model._meta.label_lower.endswith("user"):
                    kwargs[field.name] = self.user_b
                    continue

                # If FK points to RecipePost, use our post
                if rel_model._meta.model_name == "recipepost":
                    kwargs[field.name] = self.post
                    continue

                # Unknown FK model: try to create a minimal instance (may fail if it has required fields)
                try:
                    kwargs[field.name] = rel_model.objects.create()
                    continue
                except Exception:
                    # If your Notification has a required FK to another model, replace this section
                    # with a proper factory helper for that model.
                    raise AssertionError(
                        f"Notification has required FK '{field.name}' to '{rel_model.__name__}', "
                        f"but the test doesn't know how to create it. "
                        f"Add a helper factory for {rel_model.__name__} and set it here."
                    )

            # Simple field types
            if isinstance(field, (models.CharField, models.TextField)):
                kwargs[field.name] = "Test notification"
            elif isinstance(field, models.BooleanField):
                kwargs[field.name] = False
            elif isinstance(field, (models.IntegerField, models.BigIntegerField, models.SmallIntegerField)):
                kwargs[field.name] = 1
            elif isinstance(field, models.UUIDField):
                kwargs[field.name] = uuid.uuid4()
            elif isinstance(field, models.DateTimeField):
                kwargs[field.name] = timezone.now()
            elif isinstance(field, models.DateField):
                kwargs[field.name] = timezone.now().date()
            elif isinstance(field, models.TimeField):
                kwargs[field.name] = timezone.now().time()
            else:
                # If you hit this, your model has a required field type we didn't handle.
                raise AssertionError(
                    f"Unhandled required field type for '{field.name}': {field.__class__.__name__}. "
                    f"Add handling in _build_notification_kwargs()."
                )

        return kwargs

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
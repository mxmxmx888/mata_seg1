from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from recipes.models.recipe_step import RecipeStep
from recipes.tests.test_utils import make_user, make_recipe_post


class RecipeStepModelTestCase(TestCase):
    def setUp(self):
        self.user = make_user(username="@stepuser")
        self.post = make_recipe_post(author=self.user)

    def test_user_can_create_step_for_post(self):
        step = RecipeStep.objects.create(
            recipe_post=self.post,
            position=1,
            description="Chop the onions finely.",
        )
        self.assertEqual(step.recipe_post, self.post)
        self.assertEqual(step.position, 1)
        self.assertTrue(step.description)

    def test_steps_can_be_ordered_by_position(self):
        RecipeStep.objects.create(recipe_post=self.post, position=2, description="Step 2")
        RecipeStep.objects.create(recipe_post=self.post, position=1, description="Step 1")

        steps = list(RecipeStep.objects.filter(recipe_post=self.post).order_by("position"))
        self.assertEqual([s.position for s in steps], [1, 2])

    def test_description_can_be_validated_as_not_empty(self):
        step = RecipeStep(recipe_post=self.post, position=1, description="")
        with self.assertRaises(ValidationError):
            step.full_clean()

    def test_position_must_be_positive_if_validated(self):
        step = RecipeStep(recipe_post=self.post, position=0, description="Nope")
        with self.assertRaises(ValidationError):
            step.full_clean()

    def test_duplicate_position_for_same_post_not_allowed_if_constraint_exists(self):

        RecipeStep.objects.create(recipe_post=self.post, position=1, description="First")
        with self.assertRaises(IntegrityError):
            RecipeStep.objects.create(recipe_post=self.post, position=1, description="Duplicate pos")

    def test_string_representation(self):
        step = RecipeStep.objects.create(
            recipe_post=self.post,
            position=1,
            description="Mix well.",
        )
        self.assertTrue(str(step))  # just ensure __str__ returns something
from django.test import TestCase

from recipes.forms.favourite_form import FavouriteForm


class FavouriteFormTests(TestCase):
    def test_valid_name_saves(self):
        form = FavouriteForm._for_tests("My list")
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["name"], "My list")

    def test_blank_name_fails(self):
        form = FavouriteForm._for_tests("   ")
        self.assertFalse(form.is_valid())
        self.assertIn("Title is required.", form.errors.get("name", []))

    def test_strips_whitespace(self):
        form = FavouriteForm._for_tests("  Trim  ")
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["name"], "Trim")

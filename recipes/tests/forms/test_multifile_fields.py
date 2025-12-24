from django.test import TestCase
from django.utils.datastructures import MultiValueDict

from recipes.forms.recipe_forms import MultiFileInput, MultiFileField
from recipes.tests.forms.form_file_helpers import fake_image


class MultiFileInputTests(TestCase):
    def test_value_from_datadict_returns_getlist(self):
        widget = MultiFileInput()
        files = MultiValueDict({"images": [fake_image("a.jpg"), fake_image("b.jpg")]})
        out = widget.value_from_datadict(data={}, files=files, name="images")
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0].name, "a.jpg")
        self.assertEqual(out[1].name, "b.jpg")


class MultiFileFieldTests(TestCase):
    def test_clean_accepts_list(self):
        field = MultiFileField(required=False)
        first, second = fake_image("1.jpg"), fake_image("2.jpg")
        cleaned = field.clean([first, second])
        self.assertEqual(len(cleaned), 2)

    def test_clean_skips_none_entries(self):
        field = MultiFileField(required=False)
        cleaned = field.clean([None, fake_image("only.jpg")])
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned[0].name, "only.jpg")

    def test_clean_accepts_single_file(self):
        field = MultiFileField(required=False)
        cleaned = field.clean(fake_image("one.jpg"))
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned[0].name, "one.jpg")

    def test_required_raises_if_no_files(self):
        field = MultiFileField(required=True)
        with self.assertRaisesMessage(Exception, "This field is required."):
            field.clean([])

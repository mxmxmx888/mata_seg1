# recipes/forms/recipe_forms.py

from django import forms
import re

try:
    from recipes.models import RecipePost, Ingredient, RecipeStep, RecipeImage
except Exception:
    from recipes.models.recipe_post import RecipePost
    from recipes.models.ingredient import Ingredient
    from recipes.models.recipe_step import RecipeStep
    from recipes.models.recipe_post import RecipeImage


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        return files.getlist(name)

    def __init__(self, attrs=None):
        attrs = attrs or {}
        attrs.setdefault("multiple", True)
        super().__init__(attrs)


class MultiFileField(forms.FileField):
    widget = MultiFileInput

    def clean(self, data, initial=None):
        files = data or []
        if not isinstance(files, (list, tuple)):
            files = [files] if files else []

        cleaned = []
        for f in files:
            file_obj = super().to_python(f)
            if file_obj is None:
                continue
            super().validate(file_obj)
            super().run_validators(file_obj)
            cleaned.append(file_obj)

        if self.required and not cleaned and not initial:
            raise forms.ValidationError(self.error_messages["required"], code="required")

        return cleaned

CATEGORIES = [
    ("breakfast", "Breakfast"),
    ("lunch", "Lunch"),
    ("dinner", "Dinner"),
    ("dessert", "Dessert"),
    ("vegan", "Vegan"),
]

class RecipePostForm(forms.ModelForm):

    category = forms.ChoiceField(
        choices=CATEGORIES,
        required=True,
        label="Category",
        help_text="Pick one main category for this recipe.",
    )

    tags_text = forms.CharField(
        label="Tags",
        required=False,
        help_text="Separate tags with commas, e.g. pasta, quick, vegetarian",
    )
    ingredients_text = forms.CharField(
        label="Ingredients",
        required=False,
        widget=forms.Textarea(attrs={"rows": 5, "placeholder": "Example:\n2 cups Flour\nMatcha Powder | https://amazon.com/matcha"}),
        help_text="One ingredient per line. To add a shop link, use '|' separator (e.g., 'Ingredient | https://link.com').",
    )
    steps_text = forms.CharField(
        label="Steps",
        required=False,
        widget=forms.Textarea(attrs={"rows": 6}),
        help_text="One step per line.",
    )
    images = MultiFileField(
        label="Images",
        required=False,
        widget=MultiFileInput(attrs={"multiple": True}),
        help_text="Upload up to 10 images",
    )
    shop_images = MultiFileField(
        label="Shopping images",
        required=False,
        widget=MultiFileInput(attrs={"multiple": True}),
        help_text="Optional: images for shopping links (1st image → 1st link)",
    )



    class Meta:
        model = RecipePost
        fields = [
            "title",
            "description",
            "category",       
            "prep_time_min",
            "cook_time_min",
            "nutrition",
        ]

    def clean_images(self):
        files = self.files.getlist("images")
        if len(files) > 10:
            raise forms.ValidationError("You can upload up to 10 images.")
        return files
    
    def clean_shop_images(self):
        files = self.files.getlist("shop_images")
        if len(files) > 10:
            raise forms.ValidationError("You can upload up to 10 shopping images.")
        return files


    def parse_tags(self):
        raw = (self.cleaned_data.get("tags_text") or "").strip()
        tags = []
        if raw:
            parts = [p.strip() for p in raw.split(",")]
            tags = [p for p in parts if p]

        category = self.cleaned_data.get("category")
        if category:
            tags.append(f"category:{category.lower()}")

        return tags

    def _split_lines(self, key):
        text = (self.cleaned_data.get(key) or "").strip()
        if not text:
            return []
        lines = [line.strip() for line in text.splitlines()]
        return [l for l in lines if l]

    def create_ingredients(self, recipe):
        Ingredient.objects.filter(recipe_post=recipe).delete()

        lines = self._split_lines("ingredients_text")

        shop_images = list(self.cleaned_data.get("shop_images") or [])
        img_index = 0

        seen_names = set()
        position = 0

        for line in lines:
            if not line.strip():
                continue

            name = line
            url = None

            if "|" in line:
                parts = line.split("|", 1)
                name = parts[0].strip()
                raw_url = parts[1].strip()

                if raw_url:
                    if raw_url.lower().startswith(("http://", "https://")):
                        url = raw_url
                    else:
                        url = f"https://{raw_url}"

            key = name.strip().lower()
            if key in seen_names:
                continue
            seen_names.add(key)

            img_file = None
            if url and img_index < len(shop_images):
                img_file = shop_images[img_index]
                img_index += 1

            position += 1

            Ingredient.objects.create(
                recipe_post=recipe,
                name=name,
                shop_url=url,
                shop_image_upload=img_file,
                position=position,
            )




    def create_steps(self, recipe):
        RecipeStep.objects.filter(recipe_post=recipe).delete()
        lines = self._split_lines("steps_text")
        for idx, line in enumerate(lines, start=1):
            RecipeStep.objects.create(
                recipe_post=recipe,
                description=line,
                position=idx,
            )

    def create_images(self, recipe):
        files = self.files.getlist("images")
        RecipeImage.objects.filter(recipe_post=recipe).delete()

        for idx, f in enumerate(files[:10]):
            RecipeImage.objects.create(
                recipe_post=recipe,
                image=f,
                position=idx,
            )


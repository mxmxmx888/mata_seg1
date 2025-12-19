from django import forms

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
        widget=forms.Textarea(attrs={"rows": 5, "placeholder": "Example:\n2 cups Flour\n1 tsp Salt"}),
        help_text="One ingredient per line.",
    )
    shopping_links_text = forms.CharField(
        label="Shopping links",
        required=False,
        widget=forms.HiddenInput(),
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
        help_text="Add one image per shopping link (select before clicking Add).",
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
            "visibility",
        ]

    def clean_images(self):
        files = self.files.getlist("images")
        if len(files) > 10:
            raise forms.ValidationError("You can upload up to 10 images.")

        has_existing_image = False
        if getattr(self, "instance", None) and getattr(self.instance, "pk", None):
            # Editing: allow existing DB images or legacy cover image string.
            has_existing_image = RecipeImage.objects.filter(recipe_post=self.instance).exists() or bool(
                getattr(self.instance, "image", None)
            )

        if not files and not has_existing_image:
            raise forms.ValidationError("Please upload at least one image for your recipe.")

        return files
    
    def clean_shop_images(self):
        files = self.files.getlist("shop_images")
        if len(files) > 10:
            raise forms.ValidationError("You can upload up to 10 shopping images.")
        return files

    def clean(self):
        cleaned_data = super().clean()

        shopping_links = self._parse_shopping_links()
        link_count = len(shopping_links)

        existing_images = 0
        if getattr(self, "instance", None):
            existing_images = Ingredient.objects.filter(
                recipe_post=self.instance,
                shop_url__isnull=False,
                shop_url__gt="",
                shop_image_upload__isnull=False,
            ).count()

        shop_images = self.files.getlist("shop_images")
        missing = link_count - (existing_images + len(shop_images))
        if link_count and missing > 0:
            self.add_error(
                "shop_images",
                forms.ValidationError(
                    f"Add one shopping image for each shopping link (need {link_count}, provided {existing_images + len(shop_images)})."
                ),
            )

        return cleaned_data


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

    def _parse_shopping_links(self):
        text = (self.cleaned_data.get("shopping_links_text") or "").strip()
        if not text:
            return []

        items = []
        for line in text.splitlines():
            if not line.strip():
                continue

            if "|" in line:
                parts = line.split("|", 1)
                name = (parts[0] or "").strip()
                url = (parts[1] or "").strip()
            else:
                name = line.strip()
                url = ""

            if not name:
                continue

            if url:
                if url.lower().startswith(("http://", "https://")):
                    normalized_url = url
                else:
                    normalized_url = f"https://{url}"
            else:
                normalized_url = None

            items.append({"name": name, "url": normalized_url})

        return items

    def create_ingredients(self, recipe):
        existing_shop_images = list(
            Ingredient.objects.filter(
                recipe_post=recipe,
                shop_url__isnull=False,
                shop_url__gt="",
                shop_image_upload__isnull=False,
            ).order_by("position")
        )
        Ingredient.objects.filter(recipe_post=recipe).delete()

        lines = self._split_lines("ingredients_text")
        shopping_links = self._parse_shopping_links()
        shop_images = list(self.cleaned_data.get("shop_images") or [])
        img_index = 0
        existing_img_index = 0

        seen_names = set()
        position = 0

        for line in lines:
            if not line.strip():
                continue

            name = line.strip()
            key = name.lower()
            if key in seen_names:
                continue
            seen_names.add(key)

            position += 1

            Ingredient.objects.create(
                recipe_post=recipe,
                name=name,
                shop_url=None,
                shop_image_upload=None,
                position=position,
            )

        for item in shopping_links:
            name = (item.get("name") or "").strip()
            if not name:
                continue

            key = name.lower()
            if key in seen_names:
                continue
            seen_names.add(key)

            url = item.get("url") or None
            img_file = None
            if img_index < len(shop_images):
                img_file = shop_images[img_index]
                img_index += 1
            elif existing_img_index < len(existing_shop_images):
                img_file = existing_shop_images[existing_img_index].shop_image_upload
                existing_img_index += 1

            position += 1

            Ingredient.objects.create(
                recipe_post=recipe,
                name=name,
                shop_url=url,
                shop_image_upload=img_file,
                position=position,
            )



    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        super().__init__(*args, **kwargs)

        if instance:
            ingredients_qs = Ingredient.objects.filter(recipe_post=instance).order_by("position")
            ingredient_lines = []
            shopping_lines = []
            for ing in ingredients_qs:
                if getattr(ing, "shop_url", None):
                    shopping_lines.append(f"{ing.name} | {ing.shop_url}")
                else:
                    ingredient_lines.append(ing.name)

            self.fields["ingredients_text"].initial = "\n".join(ingredient_lines)
            self.fields["shopping_links_text"].initial = "\n".join(shopping_lines)


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

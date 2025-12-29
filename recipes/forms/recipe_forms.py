from django import forms

from .fields import MultiFileField, MultiFileInput

try:
    from recipes.models import RecipePost, Ingredient, RecipeStep, RecipeImage
except Exception:
    from recipes.models.recipe_post import RecipePost
    from recipes.models.ingredient import Ingredient
    from recipes.models.recipe_step import RecipeStep
    from recipes.models.recipe_post import RecipeImage

CATEGORIES = [
    ("breakfast", "Breakfast"),
    ("lunch", "Lunch"),
    ("dinner", "Dinner"),
    ("dessert", "Dessert"),
    ("vegan", "Vegan"),
]

MAX_IMAGE_UPLOAD_MB = 10
MAX_IMAGE_UPLOAD_BYTES = MAX_IMAGE_UPLOAD_MB * 1024 * 1024
MAX_SHOPPING_LINKS = 10


class RecipePostForm(forms.ModelForm):
    """Form for creating and editing recipe posts with ingredients/steps/images."""

    field_order = [
        "title",
        "images",
        "description",
        "category",
        "prep_time_min",
        "cook_time_min",
        "nutrition",
        "visibility",
        "tags_text",
        "ingredients_text",
        "serves",
        "steps_text",
        "shopping_links_text",
        "shop_images",
    ]

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
    serves = forms.IntegerField(
        label="Serves",
        required=False,
        min_value=0,
        widget=forms.TextInput(attrs={"inputmode": "numeric", "pattern": "[0-9]*"}),
        help_text="How many people this recipe serves (leave blank to hide).",
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
        """Model/field configuration for RecipePostForm."""
        model = RecipePost
        fields = [
            "title",
            "description",
            "category",
            "prep_time_min",
            "cook_time_min",
            "serves",
            "nutrition",
            "visibility",
        ]

    def clean_images(self):
        """Validate recipe images and ensure at least one is provided."""
        files = self.files.getlist("images")
        if len(files) > 10:
            raise forms.ValidationError("You can upload up to 10 images.")
        self._validate_file_sizes(files, "image")

        has_existing_image = False
        if getattr(self.instance, "pk", None) and not getattr(getattr(self.instance, "_state", None), "adding", True):
            # Editing: allow existing DB images or legacy cover image string.
            has_existing_image = RecipeImage.objects.filter(recipe_post=self.instance).exists() or bool(
                getattr(self.instance, "image", None)
            )

        if not files and not has_existing_image:
            raise forms.ValidationError("Please upload at least one image for your recipe.")

        return files

    def clean_shop_images(self):
        """Validate shopping images for count/size."""
        files = self.files.getlist("shop_images")
        if len(files) > 10:
            raise forms.ValidationError("You can upload up to 10 shopping images.")
        self._validate_file_sizes(files, "shopping image")
        return files

    def clean(self):
        """Validate shopping image counts against shopping links."""
        cleaned_data = super().clean()

        link_count = len(self._parse_shopping_links())
        self._enforce_link_limit(link_count)
        self._enforce_shop_image_requirements(link_count)
        return cleaned_data


    def parse_tags(self):
        """Parse tags_text into a list and include category marker."""
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
        """Split cleaned textarea content into stripped, non-empty lines."""
        text = (self.cleaned_data.get(key) or "").strip()
        if not text:
            return []
        lines = [line.strip() for line in text.splitlines()]
        return [l for l in lines if l]

    def _parse_shopping_links(self):
        """Parse shopping_links_text into [{'name', 'url'}] records."""
        text = (self.cleaned_data.get("shopping_links_text") or "").strip()
        if not text:
            return []

        items = []
        for line in text.splitlines():
            name, url = self._parse_shop_line(line)
            if not name:
                continue
            items.append({"name": name, "url": self._normalize_shop_url(url)})

        return items

    def _parse_shop_line(self, line: str):
        raw = line.strip()
        if not raw:
            return None, None
        if "|" in raw:
            parts = raw.split("|", 1)
            return (parts[0] or "").strip(), (parts[1] or "").strip()
        return raw, ""

    def _normalize_shop_url(self, url: str | None):
        if not url:
            return None
        if url.lower().startswith(("http://", "https://")):
            return url
        return f"https://{url}"

    def _enforce_link_limit(self, link_count: int):
        if link_count <= MAX_SHOPPING_LINKS:
            return
        self.add_error(
            "shopping_links_text",
            forms.ValidationError(
                f"Add up to {MAX_SHOPPING_LINKS} shopping links (you entered {link_count})."
            ),
        )

    def _existing_shop_image_count(self):
        if not getattr(self.instance, "pk", None):
            return 0
        if getattr(getattr(self.instance, "_state", None), "adding", True):
            return 0
        return Ingredient.objects.filter(
            recipe_post=self.instance,
            shop_url__isnull=False,
            shop_url__gt="",
            shop_image_upload__isnull=False,
        ).count()

    def _enforce_shop_image_requirements(self, link_count: int):
        uploads = self.files.getlist("shop_images")
        missing = link_count - (self._existing_shop_image_count() + len(uploads))
        if link_count and missing > 0:
            self.add_error(
                "shop_images",
                forms.ValidationError(
                    f"Add one shopping image for each shopping link (need {link_count}, provided {link_count - missing})."
                ),
            )

    def create_ingredients(self, recipe):
        """Create Ingredient rows from ingredient/shopping link inputs."""
        existing_shop_images = self._existing_shop_images_for(recipe)
        Ingredient.objects.filter(recipe_post=recipe).delete()
        seen_names = set()
        position = self._add_standard_ingredients(
            recipe,
            self._split_lines("ingredients_text"),
            seen_names,
            start_position=0,
        )
        self._add_shopping_ingredients(
            recipe,
            self._parse_shopping_links(),
            list(self.cleaned_data.get("shop_images") or []),
            existing_shop_images,
            seen_names,
            start_position=position,
        )

    def _add_standard_ingredients(self, recipe, lines, seen_names, start_position: int):
        position = start_position
        for line in lines:
            name = line.strip()
            if not name:
                continue
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
        return position

    def _add_shopping_ingredients(self, recipe, shopping_links, shop_images, existing_shop_images, seen_names, start_position: int):
        position = start_position
        for item in shopping_links:
            name = (item.get("name") or "").strip()
            if not name:
                continue
            key = name.lower()
            if key in seen_names:
                continue
            seen_names.add(key)
            position += 1
            Ingredient.objects.create(
                recipe_post=recipe,
                name=name,
                shop_url=item.get("url") or None,
                shop_image_upload=self._next_shop_image(shop_images, existing_shop_images),
                position=position,
            )

    def _existing_shop_images_for(self, recipe):
        return list(
            Ingredient.objects.filter(
                recipe_post=recipe,
                shop_url__isnull=False,
                shop_url__gt="",
                shop_image_upload__isnull=False,
            ).order_by("position")
        )

    def _next_shop_image(self, shop_images, existing_shop_images):
        if shop_images:
            return shop_images.pop(0)
        if existing_shop_images:
            return existing_shop_images.pop(0).shop_image_upload
        return None



    def __init__(self, *args, **kwargs):
        """Populate initial fields when editing an existing recipe."""
        instance = kwargs.get("instance")
        super().__init__(*args, **kwargs)

        self._set_nutrition_placeholder()

        if instance:
            self._prefill_tags(instance)
            self._prefill_serves(instance)
            self._prefill_ingredients(instance)
            self._prefill_steps(instance)

    def _set_nutrition_placeholder(self):
        nutrition_field = self.fields.get("nutrition")
        if not nutrition_field:
            return
        nutrition_field.widget.attrs.setdefault(
            "placeholder",
            "Example: 320 kcal; Protein 20g; Carbs 30g; Fat 10g",
        )

    def _prefill_tags(self, instance):
        tags = getattr(instance, "tags", None) or []
        tag_list = [tag for tag in tags if not str(tag).lower().startswith("category:")]
        if tag_list:
            self.fields["tags_text"].initial = ", ".join(tag_list)

    def _prefill_serves(self, instance):
        serves = getattr(instance, "serves", 0) or 0
        if serves:
            self.fields["serves"].initial = serves  # pragma: no cover - optional initial value

    def _prefill_ingredients(self, instance):
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

    def _prefill_steps(self, instance):
        steps_qs = RecipeStep.objects.filter(recipe_post=instance).order_by("position")
        self.fields["steps_text"].initial = "\n".join(step.description for step in steps_qs)

    def create_steps(self, recipe):
        """Create RecipeStep rows from parsed steps_text."""
        RecipeStep.objects.filter(recipe_post=recipe).delete()
        lines = self._split_lines("steps_text")
        for idx, line in enumerate(lines, start=1):
            RecipeStep.objects.create(
                recipe_post=recipe,
                description=line,
                position=idx,
            )

    def create_images(self, recipe):
        """Create RecipeImage rows and set legacy cover image when needed."""
        files = self.files.getlist("images")
        if not files:
            return

        RecipeImage.objects.filter(recipe_post=recipe).delete()

        for idx, f in enumerate(files[:10]):
            RecipeImage.objects.create(
                recipe_post=recipe,
                image=f,
                position=idx,
            )

    def _validate_file_sizes(self, files, label):
        """Raise validation error when any file exceeds the configured limit."""
        too_large = [f.name for f in files if getattr(f, "size", 0) > MAX_IMAGE_UPLOAD_BYTES]
        if not too_large:
            return
        names = ", ".join(too_large)
        raise forms.ValidationError(
            f"Each {label} must be {MAX_IMAGE_UPLOAD_MB}MB or smaller. Remove: {names}."
        )

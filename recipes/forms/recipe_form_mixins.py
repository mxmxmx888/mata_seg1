from django import forms

from recipes.models import Ingredient

MAX_SHOPPING_LINKS = 10


class ShoppingFieldHelpers:
    """Shared helpers for shopping link parsing and ingredient management."""

    def _split_lines(self, key):
        """Split cleaned textarea content into stripped, non-empty lines."""
        text = (self.cleaned_data.get(key) or "").strip()
        if not text:
            return []
        lines = [line.strip() for line in text.splitlines()]
        return [line for line in lines if line]

    def _parse_shop_line(self, line: str):
        """Parse a shopping link line into name and URL.
        
        Format: 'name' or 'name|url'. Returns (name, url) tuple.
        """
        raw = line.strip()
        if not raw:
            return None, None
        if "|" in raw:
            parts = raw.split("|", 1)
            return (parts[0] or "").strip(), (parts[1] or "").strip()
        return raw, ""

    def _normalize_shop_url(self, url: str | None):
        """Normalize URL by adding https:// prefix if missing."""
        if not url:
            return None
        if url.lower().startswith(("http://", "https://")):
            return url
        return f"https://{url}"

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

    def _enforce_link_limit(self, link_count: int):
        """Add validation error if link_count exceeds MAX_SHOPPING_LINKS."""
        if link_count <= MAX_SHOPPING_LINKS:
            return
        self.add_error(
            "shopping_links_text",
            forms.ValidationError(
                f"Add up to {MAX_SHOPPING_LINKS} shopping links (you entered {link_count})."
            ),
        )

    def _existing_shop_image_count(self):
        """Count existing shopping images for the recipe instance."""
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
        """Validate that enough shopping images are provided for all links."""
        uploads = self.files.getlist("shop_images")
        missing = link_count - (self._existing_shop_image_count() + len(uploads))
        if link_count and missing > 0:
            self.add_error(
                "shop_images",
                forms.ValidationError(
                    f"Add one shopping image for each shopping link (need {link_count}, provided {link_count - missing})."
                ),
            )

    def _existing_shop_images_for(self, recipe):
        """Get list of existing shopping ingredients with images for the recipe."""
        return list(
            Ingredient.objects.filter(
                recipe_post=recipe,
                shop_url__isnull=False,
                shop_url__gt="",
                shop_image_upload__isnull=False,
            ).order_by("position")
        )

    def _next_shop_image(self, shop_images, existing_shop_images):
        """Get next available shopping image from new uploads or existing images."""
        if shop_images:
            return shop_images.pop(0)
        if existing_shop_images:
            return existing_shop_images.pop(0).shop_image_upload
        return None

    def _add_standard_ingredients(self, recipe, lines, seen_names, start_position: int):
        """Create standard (non-shopping) ingredients from lines.
        
        Returns the last position used.
        """
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

    def _iter_unique_shopping_items(self, shopping_links, seen_names):
        """Yield unique (name, url) tuples from shopping_links, skipping duplicates."""
        for item in shopping_links:
            name = (item.get("name") or "").strip()
            if not name:
                continue
            key = name.lower()
            if key in seen_names:
                continue
            seen_names.add(key)
            yield name, item.get("url") or None

    def _add_shopping_ingredients(
        self,
        recipe,
        shopping_links,
        shop_images,
        existing_shop_images,
        seen_names,
        start_position: int,
    ):
        """Create shopping ingredients with images from parsed links.
        
        Returns the last position used.
        """
        position = start_position
        for name, url in self._iter_unique_shopping_items(shopping_links, seen_names):
            position += 1
            Ingredient.objects.create(
                recipe_post=recipe,
                name=name,
                shop_url=url,
                shop_image_upload=self._next_shop_image(shop_images, existing_shop_images),
                position=position,
            )
        return position

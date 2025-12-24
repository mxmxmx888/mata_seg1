from rest_framework import serializers
from recipes.models import RecipePost


class RecipeSerializer(serializers.ModelSerializer):
    """Serializer for RecipePost with common fields."""
    primary_image_url = serializers.CharField(read_only=True)

    class Meta:
        model = RecipePost
        fields = [
            "id",
            "author",
            "title",
            "description",
            "category",
            "tags",
            "prep_time_min",
            "cook_time_min",
            "serves",
            "nutrition",
            "visibility",
            "saved_count",
            "published_at",
            "created_at",
            "updated_at",
            "is_hidden",
            "primary_image_url",
        ]
        read_only_fields = [
            "id",
            "author",
            "saved_count",
            "published_at",
            "created_at",
            "updated_at",
            "primary_image_url",
        ]

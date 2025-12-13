from django.db.models import Q
from recipes.models.followers import Follower

class PrivacyService:
    def __init__(self, follower_model=Follower):
        self.follower_model = follower_model

    def is_private(self, user):
        return bool(getattr(user, "is_private", False))

    def is_follower(self, viewer, author):
        if not viewer or not getattr(viewer, "is_authenticated", False):
            return False
        if viewer == author:
            return True
        return self.follower_model.objects.filter(
            follower=viewer, author=author
        ).exists()

    def can_view_profile(self, viewer, author):
        if not self.is_private(author):
            return True
        return self.is_follower(viewer, author)

    def filter_visible_posts(self, queryset, viewer):
        if viewer and getattr(viewer, "is_authenticated", False):
            return queryset.filter(
                Q(author__is_private=False)
                | Q(author=viewer)
                | Q(author__followers__follower=viewer)
            ).distinct()
        return queryset.filter(author__is_private=False)

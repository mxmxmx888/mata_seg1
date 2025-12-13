from django.db.models import Q
from recipes.models.followers import Follower
from recipes.models.close_friend import CloseFriend
from recipes.models.recipe_post import RecipePost


class PrivacyService:
    def __init__(self, follower_model=Follower, close_friend_model=CloseFriend):
        self.follower_model = follower_model
        self.close_friend_model = close_friend_model

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

    def is_close_friend(self, viewer, author):
        if not viewer or not getattr(viewer, "is_authenticated", False):
            return False
        if viewer == author:
            return True
        return self.close_friend_model.objects.filter(
            owner=author, friend=viewer
        ).exists()

    def can_view_profile(self, viewer, author):
        if not self.is_private(author):
            return True
        return self.is_follower(viewer, author)

    def can_view_post(self, viewer, post):
        if viewer == post.author:
            return True

        if self.is_private(post.author) and not self.is_follower(viewer, post.author):
            return False

        visibility = getattr(post, "visibility", RecipePost.VISIBILITY_PUBLIC)

        if visibility == RecipePost.VISIBILITY_PUBLIC:
            return True
        if visibility == RecipePost.VISIBILITY_FOLLOWERS:
            return self.is_follower(viewer, post.author)
        if visibility == RecipePost.VISIBILITY_CLOSE_FRIENDS:
            return self.is_close_friend(viewer, post.author)
        return False

    def filter_visible_posts(self, queryset, viewer):
        if viewer and getattr(viewer, "is_authenticated", False):
            allowed = (
                Q(visibility=RecipePost.VISIBILITY_PUBLIC)
                | Q(
                    visibility=RecipePost.VISIBILITY_FOLLOWERS,
                    author__followers__follower=viewer,
                )
                | Q(
                    visibility=RecipePost.VISIBILITY_CLOSE_FRIENDS,
                    author__close_friend_owner__friend=viewer,
                )
                | Q(author=viewer)
            )
            profile_gate = (
                Q(author__is_private=False)
                | Q(author=viewer)
                | Q(author__followers__follower=viewer)
            )
            return queryset.filter(profile_gate & allowed).distinct()

        return queryset.filter(
            author__is_private=False, visibility=RecipePost.VISIBILITY_PUBLIC
        )

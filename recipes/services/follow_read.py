"""Read-only helpers for follower/following/close-friend queries."""

from recipes.models import Follower, CloseFriend


class FollowReadService:
    """Provide query helpers for follow relationships."""

    def __init__(self, follower_model=Follower, close_friend_model=CloseFriend):
        self.follower_model = follower_model
        self.close_friend_model = close_friend_model

    def followers_qs(self, user):
        """Return queryset of followers for the given user."""
        return self.follower_model.objects.filter(author=user).select_related("follower")

    def following_qs(self, user):
        """Return queryset of users the given user follows."""
        return self.follower_model.objects.filter(follower=user).select_related("author")

    def close_friend_ids(self, user):
        """Return close friend user IDs for the given user."""
        return set(
            self.close_friend_model.objects.filter(owner=user).values_list("friend_id", flat=True)
        )

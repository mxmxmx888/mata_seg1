"""Profile-related services and dependency factory."""

from recipes.repos.post_repo import PostRepo
from recipes.repos.user_repo import UserRepo
from recipes.models import Favourite, FavouriteItem, Follower, CloseFriend, FollowRequest, RecipePost
from recipes.services.privacy import PrivacyService
from recipes.services.follow import FollowService
from recipes.services.follow_read import FollowReadService
from recipes.views.profile_data_helpers import profile_data_for_user, collections_for_user


class ProfileDisplayService:
    """Provide avatar URLs for profile editing and navbar contexts."""

    def __init__(self, user):
        """Bind the service to a user instance."""
        self.user = user

    def _user_avatar(self):
        """Return the best available avatar URL or blank when unauthenticated."""
        if not self.user or not getattr(self.user, "is_authenticated", False):
            return ""
        return getattr(self.user, "avatar_url", "") or ""

    def editing_avatar_url(self):
        """Return avatar URL used in profile editing contexts."""
        return self._user_avatar()

    def navbar_avatar_url(self):
        """Return avatar URL used in navbar display."""
        return self._user_avatar()


class ProfileDepsFactory:
    """Factory to assemble ProfileDeps dependencies without view-layer imports."""

    def __init__(self):
        self.post_repo = PostRepo()
        self.user_repo = UserRepo()
        self.privacy_service = PrivacyService()
        self.follow_service_factory = FollowService
        self.profile_data_for_user = profile_data_for_user
        self.collections_for_user = collections_for_user
        self.follower_model = Follower
        self.close_friend_model = CloseFriend
        self.follow_request_model = FollowRequest
        self.favourite_model = Favourite
        self.favourite_item_model = FavouriteItem
        self.recipe_post_model = RecipePost
        self.follow_read_service = FollowReadService(self.follower_model, self.close_friend_model)

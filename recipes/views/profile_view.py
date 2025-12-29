"""Profile page views and dependency wiring for profile logic helpers."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required

from recipes.forms import PasswordForm, UserForm
from recipes.repos.post_repo import PostRepo
from recipes.repos.user_repo import UserRepo
from recipes.models.follow_request import FollowRequest
from recipes.models.close_friend import CloseFriend
from recipes.services import PrivacyService, FollowService
from recipes.models import Follower, Favourite, RecipePost
from recipes.models.favourite_item import FavouriteItem
from recipes.views.profile_data_helpers import profile_data_for_user, collections_for_user
from recipes.views import profile_view_logic as logic

post_repo = PostRepo()
user_repo = UserRepo()
privacy_service = PrivacyService()
follow_service_factory = FollowService
_profile_data_for_user = profile_data_for_user
_collections_for_user = collections_for_user
FOLLOW_LIST_PAGE_SIZE = logic.FOLLOW_LIST_PAGE_SIZE


def _deps():
    return logic.ProfileDeps(
        messages=messages,
        user_form_cls=UserForm,
        password_form_cls=PasswordForm,
        follow_service_factory=follow_service_factory,
        privacy_service=privacy_service,
        post_repo=post_repo,
        user_repo=user_repo,
        profile_data_for_user=_profile_data_for_user,
        collections_for_user=_collections_for_user,
        follower_model=Follower,
        close_friend_model=CloseFriend,
        follow_request_model=FollowRequest,
        favourite_model=Favourite,
        favourite_item_model=FavouriteItem,
        recipe_post_model=RecipePost,
    )


def _follow_context(profile_user, viewer):
    """Expose follow context for tests and callers with patched deps."""
    return logic.follow_context(profile_user, viewer, _deps())


@login_required
def profile_follow_list(request):
    """Return paginated followers/following/close friend candidates as HTML chunks."""
    return logic.profile_follow_list_response(request, _deps())


@login_required
def profile(request):
    """Render the profile page for the requested user (or self)."""
    return logic.profile_response(request, _deps())

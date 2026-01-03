"""Profile page views and dependency wiring for profile logic helpers."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required

from recipes.forms import PasswordForm, UserForm
import recipes.views.profile_view_logic as logic
from recipes.services.profile import ProfileDepsFactory

profile_deps_factory = ProfileDepsFactory()
_profile_data_for_user = profile_deps_factory.profile_data_for_user
_collections_for_user = profile_deps_factory.collections_for_user
privacy_service = profile_deps_factory.privacy_service
follow_service_factory = profile_deps_factory.follow_service_factory
Favourite = profile_deps_factory.favourite_model
FavouriteItem = profile_deps_factory.favourite_item_model
FOLLOW_LIST_PAGE_SIZE = logic.FOLLOW_LIST_PAGE_SIZE


def _deps():
    return logic.ProfileDeps(
        messages=messages,
        user_form_cls=UserForm,
        password_form_cls=PasswordForm,
        follow_service_factory=follow_service_factory,
        privacy_service=privacy_service,
        post_repo=profile_deps_factory.post_repo,
        user_repo=profile_deps_factory.user_repo,
        profile_data_for_user=_profile_data_for_user,
        collections_for_user=_collections_for_user,
        follow_read_service=profile_deps_factory.follow_read_service,
        follower_model=profile_deps_factory.follower_model,
        close_friend_model=profile_deps_factory.close_friend_model,
        follow_request_model=profile_deps_factory.follow_request_model,
        favourite_model=Favourite,
        favourite_item_model=FavouriteItem,
        recipe_post_model=profile_deps_factory.recipe_post_model,
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

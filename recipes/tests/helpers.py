from django.urls import reverse
from django.utils import timezone
import uuid

from recipes.models import User
from recipes.models.recipe_post import RecipePost

def reverse_with_next(url_name, next_url):
    """Extended version of reverse to generate URLs with redirects"""
    url = reverse(url_name)
    url += f"?next={next_url}"
    return url

def make_user(**kwargs):
    username = kwargs.pop("username", "@johndoe")
    if not username.startswith("@"):
        username = "@" + username

    email = kwargs.pop(
        "email",
        f"{username[1:]}_{uuid.uuid4().hex[:6]}@example.org"
    )

    password = kwargs.pop("password", "Password123")

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=kwargs.pop("first_name", "John"),
        last_name=kwargs.pop("last_name", "Doe"),
        bio=kwargs.pop("bio", "Test bio"),
        **kwargs,
    )
    return user


def make_recipe_post(
    *,
    author=None,
    title="test post",
    description="desc",
    published=True,
    **extra,
):
    """
    creates and returns a recipe post. published=True sets published_at.
    """
    if author is None:
        author = make_user()

    return RecipePost.objects.create(
        author=author,
        title=title,
        description=description,
        published_at=timezone.now() if published else None,
        **extra,
    )

class LogInTester:
    """Class support login in tests."""
 
    def _is_logged_in(self):
        """Returns True if a user is logged in.  False otherwise."""

        return '_auth_user_id' in self.client.session.keys()

class MenuTesterMixin:
    """Class to extend tests with tools to check the presents of menu items."""

    menu_urls = [
        reverse('password'), reverse('profile'), reverse('log_out')
    ]

    def assert_menu(self, response):
        """Check that menu is present."""

        for url in self.menu_urls:
            with self.assertHTML(response, f'a[href="{url}"]'):
                pass

    def assert_no_menu(self, response):
        """Check that no menu is present."""
        
        for url in self.menu_urls:
            self.assertNotHTML(response, f'a[href="{url}"]')

    
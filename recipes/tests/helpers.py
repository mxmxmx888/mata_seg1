from django.urls import reverse
from django.test import SimpleTestCase
import uuid
from recipes.models import User
from recipes.models.recipe_post import RecipePost
from django.utils import timezone

def reverse_with_next(url_name, next_url):
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
    def _is_logged_in(self):
        return '_auth_user_id' in self.client.session.keys()

class MenuTesterMixin:
    def get_menu_urls(self):
        return [
            reverse('password'), 
            reverse('profile'), 
            reverse('log_out')
        ]

    def assert_menu(self, response):
        for url in self.get_menu_urls():
            self.assertContains(response, f'href="{url}"')

    def assert_no_menu(self, response):
        for url in self.get_menu_urls():
            self.assertNotContains(response, f'href="{url}"')
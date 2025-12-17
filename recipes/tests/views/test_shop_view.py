from django.test import TestCase
from django.urls import reverse
from recipes.models import User, RecipePost, Ingredient, Favourite, FavouriteItem
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

class ShopViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='johndoe', 
            email='test@example.com', 
            password='Password123'
        )
        self.post = RecipePost.objects.create(
            author=self.user, 
            title="Cake", 
            description="Delicious"
        )
        self.ing = Ingredient.objects.create(
            recipe_post=self.post, 
            name="flour", 
            shop_url="http://shop.com",
            position=1
        )
        self.url = reverse('shop')
        site = Site.objects.get_current()
        provider = SocialApp.objects.create(
            provider="google",
            name="Google",
            client_id="fake-client-id",
            secret="fake-secret",
        )
        provider.sites.add(site)

    def test_login_required(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('log_in')}?next={self.url}")

    def test_shop_view_renders_items(self):
        self.client.login(email='test@example.com', password='Password123')
        fav = Favourite.objects.create(user=self.user, name="My List")
        
        FavouriteItem.objects.create(favourite=fav, recipe_post=self.post)
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "flour")
        self.assertContains(response, "http://shop.com")

    def test_shop_view_excludes_empty_url(self):
        Ingredient.objects.create(
            recipe_post=self.post, 
            name="water", 
            shop_url="",
            position=2
        )
        self.client.login(email='test@example.com', password='Password123')
        fav = Favourite.objects.create(user=self.user, name="My List")
        
        FavouriteItem.objects.create(favourite=fav, recipe_post=self.post)
        
        response = self.client.get(self.url)
        self.assertContains(response, "flour")
        self.assertNotContains(response, "water")

    def test_shop_view_ajax(self):
        self.client.login(email='test@example.com', password='Password123')
        fav = Favourite.objects.create(user=self.user, name="My List")
        
        FavouriteItem.objects.create(favourite=fav, recipe_post=self.post)
        
        response = self.client.get(self.url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'partials/shop/shop_items.html')

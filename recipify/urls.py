"""
URL configuration for recipify project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from recipes import views
from recipes.views.post_mock_view import mock_post_detail
from recipes.views.recipe_views import (
    recipe_create,
    recipe_detail,
    my_recipes,
    saved_recipes,
    toggle_favourite,
    toggle_like,
    delete_my_recipe,
    toggle_follow,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('log_in/', views.LogInView.as_view(), name='log_in'),
    path('log_out/', views.log_out, name='log_out'),
    path('sign_up/', views.SignUpView.as_view(), name='sign_up'),
    path('password/reset/', views.PasswordResetRequestView.as_view(), name='password_reset'),
    path('password/reset/done/', views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('username/reset/', views.UsernameResetRequestView.as_view(), name='username_reset'),
    path('username/reset/done/', views.UsernameResetDoneView.as_view(), name='username_reset_done'),
    path('password/', views.PasswordView.as_view(), name='password'),
    path('profile/', views.profile, name='profile'),
    path('profile/collections/<slug:slug>/', views.collection_detail, name='collection_detail'),
    path("post/mock/", mock_post_detail, name="post_mock"),
    path('recipes/create/', recipe_create, name='recipe_create'),
    path('recipes/<uuid:post_id>/', recipe_detail, name='recipe_detail'),
    path('recipes/<uuid:post_id>/favourite/', toggle_favourite, name='toggle_favourite'),
    path('recipes/<uuid:post_id>/like/', toggle_like, name='toggle_like'),
    path('my-recipes/', my_recipes, name='my_recipes'),
    path('my-recipes/<uuid:post_id>/delete/', delete_my_recipe, name='delete_my_recipe'),
    path('saved/', saved_recipes, name='saved_recipes'),
    path('api/profile', views.profile_api, name='profile_api'),
    path('u/<str:username>/follow/', toggle_follow, name='toggle_follow'),
    path('report/<str:content_type>/<uuid:object_id>/', views.report_content, name='report_content'),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

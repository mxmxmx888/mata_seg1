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
from recipes.views import profile_view
from recipes import views
from recipes.views.recipe_views import (
    recipe_create,
    recipe_edit,
    recipe_detail,
    saved_recipes,
    toggle_favourite,
    toggle_like,
    delete_my_recipe,
    toggle_follow,
)
from recipes.views.follow_request_views import accept_follow_request, reject_follow_request
from recipes.views.collection_views import collections_overview, collection_detail, update_collection, delete_collection
from recipes.views.social_views import remove_follower, remove_following, add_close_friend, remove_close_friend
from recipes.views.api_views import RecipeListApi, RecipeDetailApi

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
    path('collections/', collections_overview, name='collections'),
    path('profile/collections/<slug:slug>/', collection_detail, name='collection_detail'),
    path('profile/collections/<slug:slug>/edit/', update_collection, name='update_collection'),
    path('profile/collections/<slug:slug>/delete/', delete_collection, name='delete_collection'),
    path('recipes/create/', recipe_create, name='recipe_create'),
    path('recipes/<uuid:post_id>/', recipe_detail, name='recipe_detail'),
    path("recipes/<uuid:post_id>/edit/", recipe_edit, name="recipe_edit"),
    path('recipes/<uuid:post_id>/favourite/', toggle_favourite, name='toggle_favourite'),
    path('recipes/<uuid:post_id>/like/', toggle_like, name='toggle_like'),
    path('my-recipes/<uuid:post_id>/delete/', delete_my_recipe, name='delete_my_recipe'),
    path('saved/', saved_recipes, name='saved_recipes'),
    path('api/profile', views.profile_api, name='profile_api'),
    path('u/<str:username>/follow/', toggle_follow, name='toggle_follow'),
    path('followers/<str:username>/remove/', remove_follower, name='remove_follower'),
    path('following/<str:username>/remove/', remove_following, name='remove_following'),
    path('close-friends/<str:username>/add/', add_close_friend, name='add_close_friend'),
    path('close-friends/<str:username>/remove/', remove_close_friend, name='remove_close_friend'),
    path('follow-requests/<uuid:request_id>/accept/', accept_follow_request, name='accept_follow_request'),
    path('follow-requests/<uuid:request_id>/reject/', reject_follow_request, name='reject_follow_request'),
    path('report/<str:content_type>/<uuid:object_id>/', views.report_content, name='report_content'),
    path('shop/', views.shop, name='shop'),
    path('api/notifications/read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('recipes/<uuid:post_id>/comment/', views.add_comment, name='add_comment'),
    path('comments/<uuid:comment_id>/delete/', views.delete_comment, name='delete_comment'),
    path('api/recipes/', RecipeListApi.as_view(), name='recipe_list_api'),
    path('api/recipes/<uuid:pk>/', RecipeDetailApi.as_view(), name='recipe_detail_api'),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

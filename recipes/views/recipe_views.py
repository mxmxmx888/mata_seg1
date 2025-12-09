from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from recipes.forms.recipe_forms import RecipePostForm
from recipes.repos.post_repo import PostRepo

try:
    from recipes.models import RecipePost, Ingredient, RecipeStep, Favourite, Like
except Exception:
    from recipes.models.recipe_post import RecipePost
    from recipes.models.ingredient import Ingredient
    from recipes.models.recipe_step import RecipeStep
    from recipes.models.favourite import Favourite
    from recipes.models.like import Like

try:
    from recipes.models.followers import Follower
except Exception:
    from recipes.models import Follower

User = get_user_model()
post_repo = PostRepo()


@login_required
def recipe_create(request):
    if request.method == "POST":
        form = RecipePostForm(request.POST, request.FILES or None)
        if form.is_valid():
            cleaned = form.cleaned_data
            tags_list = form.parse_tags()

            recipe = RecipePost.objects.create(
                author=request.user,
                title=cleaned["title"],
                description=cleaned.get("description") or "",
                image=cleaned.get("image") or None,
                prep_time_min=cleaned.get("prep_time_min") or 0,
                cook_time_min=cleaned.get("cook_time_min") or 0,
                nutrition=cleaned.get("nutrition") or "",
                tags=tags_list,
                published_at=timezone.now(),
            )

            form.create_ingredients(recipe)
            form.create_steps(recipe)

            messages.success(request, "Recipe created.")
            return redirect("recipe_detail", post_id=recipe.id)
    else:
        form = RecipePostForm()

    return render(request, "create_recipe.html", {"form": form})


def recipe_detail(request, post_id):
    recipe = get_object_or_404(RecipePost, id=post_id)
    ingredients = Ingredient.objects.filter(recipe_post=recipe).order_by("position")
    steps = RecipeStep.objects.filter(recipe_post=recipe).order_by("position")

    user_liked = False
    user_saved = False
    is_following_author = False

    if request.user.is_authenticated:
        user_liked = Like.objects.filter(user=request.user, recipe_post=recipe).exists()
        user_saved = Favourite.objects.filter(user=request.user, recipe_post=recipe).exists()
        is_following_author = Follower.objects.filter(
            follower=request.user,
            author=recipe.author,
        ).exists()

    context = {
        "post": recipe,
        "ingredients": ingredients,
        "steps": steps,
        "user_liked": user_liked,
        "user_saved": user_saved,
        "is_following_author": is_following_author,
    }
    return render(request, "recipe_detail.html", context)


@login_required
def my_recipes(request):
    posts = post_repo.list_for_user(
        request.user.id,
        order_by=("-created_at",),
    )
    return render(request, "my_recipes.html", {"posts": posts})


@login_required
def saved_recipes(request):
    fav_ids = Favourite.objects.filter(user=request.user).values_list(
        "recipe_post_id", flat=True
    )
    posts = RecipePost.objects.filter(id__in=fav_ids).order_by("-created_at")
    return render(request, "saved_recipes.html", {"posts": posts})


@login_required
def delete_my_recipe(request, post_id):
    recipe = get_object_or_404(RecipePost, id=post_id, author=request.user)

    if request.method == "POST":
        recipe.delete()
        messages.success(request, "Recipe deleted.")
        return redirect("my_recipes")

    return redirect("recipe_detail", post_id=recipe.id)


@login_required
def toggle_favourite(request, post_id):
    recipe = get_object_or_404(RecipePost, id=post_id)
    existing = Favourite.objects.filter(user=request.user, recipe_post=recipe)

    if existing.exists():
        existing.delete()
        RecipePost.objects.filter(id=recipe.id).update(
            saved_count=max(0, (recipe.saved_count or 0) - 1)
        )
    else:
        Favourite.objects.create(user=request.user, recipe_post=recipe)
        RecipePost.objects.filter(id=recipe.id).update(
            saved_count=(recipe.saved_count or 0) + 1
        )

    if request.headers.get("HX-Request") or request.headers.get("x-requested-with") == "XMLHttpRequest":
        return HttpResponse(status=204)

    return redirect(request.META.get("HTTP_REFERER") or reverse("recipe_detail", args=[recipe.id]))


@login_required
def toggle_like(request, post_id):
    recipe = get_object_or_404(RecipePost, id=post_id)
    existing = Like.objects.filter(user=request.user, recipe_post=recipe)

    if existing.exists():
        existing.delete()
    else:
        Like.objects.create(user=request.user, recipe_post=recipe)

    if request.headers.get("HX-Request") or request.headers.get("x-requested-with") == "XMLHttpRequest":
        return HttpResponse(status=204)

    return redirect(request.META.get("HTTP_REFERER") or reverse("recipe_detail", args=[recipe.id]))


@login_required
def toggle_follow(request, username):
    target_user = get_object_or_404(User, username=username)

    if target_user == request.user:
        if request.headers.get("HX-Request") or request.headers.get("x-requested-with") == "XMLHttpRequest":
            return HttpResponse(status=204)
        return redirect(request.META.get("HTTP_REFERER") or reverse("dashboard"))

    existing = Follower.objects.filter(
        follower=request.user,
        author=target_user,
    )

    if existing.exists():
        existing.delete()
    else:
        Follower.objects.create(follower=request.user, author=target_user)

    if request.headers.get("HX-Request") or request.headers.get("x-requested-with") == "XMLHttpRequest":
        return HttpResponse(status=204)

    return redirect(request.META.get("HTTP_REFERER") or reverse("dashboard"))

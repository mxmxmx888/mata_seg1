from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from recipes.forms.recipe_forms import RecipePostForm
from recipes.repos.post_repo import PostRepo
from recipes.forms.comment_form import CommentForm

try:
    from recipes.models import RecipePost, Ingredient, RecipeStep, Favourite, Like, Comment
    from recipes.models.favourite_item import FavouriteItem
except Exception:
    from recipes.models.recipe_post import RecipePost
    from recipes.models.ingredient import Ingredient
    from recipes.models.recipe_step import RecipeStep
    from mata_seg1.recipes.models.collection import Favourite
    from recipes.models.like import Like
    from recipes.models.comment import Comment

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
                prep_time_min=cleaned.get("prep_time_min") or 0,
                cook_time_min=cleaned.get("cook_time_min") or 0,
                nutrition=cleaned.get("nutrition") or "",
                tags=tags_list,
                category=cleaned.get("category") or "",
                published_at=timezone.now(),
            )

            form.create_ingredients(recipe)
            form.create_steps(recipe)
            form.create_images(recipe)

            primary_image = recipe.images.first()
            if primary_image and primary_image.image:
                recipe.image = primary_image.image.url
                recipe.save(update_fields=["image"])

            messages.success(request, "Recipe created.")
            return redirect("recipe_detail", post_id=recipe.id)
    else:
        form = RecipePostForm()

    return render(request, "create_recipe.html", {"form": form})


@login_required
def recipe_detail(request, post_id):
    recipe = get_object_or_404(RecipePost, id=post_id)
    ingredients_qs = Ingredient.objects.filter(recipe_post=recipe).order_by("position")
    steps_qs = RecipeStep.objects.filter(recipe_post=recipe).order_by("position")
    images_qs = recipe.images.all()
    
    # FETCH COMMENTS
    comments = recipe.comments.select_related('user').order_by("-created_at")

    user_liked = False
    user_saved = False
    is_following_author = False

    if request.user.is_authenticated:
        user_liked = Like.objects.filter(user=request.user, recipe_post=recipe).exists()

        # saved = recipe exists in the user's default "favourites" collection
        user_saved = FavouriteItem.objects.filter(
            favourite__user=request.user,
            favourite__name="favourites",
            recipe_post=recipe,
        ).exists()

        is_following_author = Follower.objects.filter(
            follower=request.user,
            author=recipe.author,
        ).exists()

    likes_count = Like.objects.filter(recipe_post=recipe).count()

    # saves = how many times this recipe appears in any collection
    saves_count = FavouriteItem.objects.filter(recipe_post=recipe).count()

    image_url = None
    if images_qs:
        first_image = images_qs[0]
        try:
            image_url = first_image.image.url
        except ValueError:
            image_url = None
    if not image_url:
        image_url = recipe.image or "https://placehold.co/1200x800/0f0f14/ffffff?text=Recipe"

    gallery_images = []
    if images_qs.count() > 1:
        for extra in images_qs[1:]:
            try:
                gallery_images.append(extra.image.url)
            except ValueError:
                continue
    author_handle = getattr(recipe.author, "username", "")
    total_time = (recipe.prep_time_min or 0) + (recipe.cook_time_min or 0)
    cook_time = f"{total_time} min" if total_time else "N/A"
    serves = getattr(recipe, "serves", None) or 1
    summary = recipe.description or ""
    tags_list = recipe.tags or []
    post_date = (recipe.published_at or recipe.created_at or timezone.now()).strftime("%b %d, %Y")
    source_link = request.build_absolute_uri(reverse("recipe_detail", args=[recipe.id]))
    source_label = "Recipi"

    ingredients = list(ingredients_qs)
    shop_ingredients = [ing for ing in ingredients if getattr(ing, "shop_url", None) and ing.shop_url.strip()]
    steps = [s.description for s in steps_qs]

    context = {
        "recipe": recipe,
        "post": recipe,
        "image_url": image_url,
        "author_handle": author_handle,
        "title": recipe.title,
        "cook_time": cook_time,
        "serves": serves,
        "ingredients": ingredients,
        "shop_ingredients": shop_ingredients,
        "steps": steps,
        "summary": summary,
        "tags": tags_list,
        "post_date": post_date,
        "source_link": source_link,
        "source_label": source_label,
        "user_liked": user_liked,
        "user_saved": user_saved,
        "is_following_author": is_following_author,
        "likes_count": likes_count,
        "saves_count": saves_count,
        "comments": comments, # Pass actual comments
        "comment_form": CommentForm(), # Pass empty form
        "gallery_images": gallery_images,
        "video_url": None,
        "view_similar": [],
    }
    return render(request, "post_detail.html", context)

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

@login_required
def add_comment(request, post_id):
    recipe = get_object_or_404(RecipePost, id=post_id)
    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.recipe_post = recipe
            comment.user = request.user
            comment.save()
            messages.success(request, "Comment posted.")
        else:
            messages.error(request, "Error posting comment.")
    
    return redirect("recipe_detail", post_id=recipe.id)

@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Security check: only allow the author to delete
    if comment.user != request.user:
        messages.error(request, "You are not allowed to delete this comment.")
        return redirect('recipe_detail', post_id=comment.recipe_post.id)
        
    post_id = comment.recipe_post.id
    comment.delete()
    messages.success(request, "Comment deleted.")
    return redirect('recipe_detail', post_id=post_id)

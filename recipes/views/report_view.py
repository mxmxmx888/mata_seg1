from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from recipes.models.recipe_post import RecipePost
from recipes.models.comment import Comment
from recipes.forms.report_form import ReportForm

@login_required
def report_content(request, content_type, object_id):
    """
    Generic view to report either a recipe or a comment.
    content_type should be 'recipe' or 'comment'.
    """
    recipe = None
    comment = None

    # Identify target
    if content_type == 'recipe':
        recipe = get_object_or_404(RecipePost, id=object_id)
    elif content_type == 'comment':
        comment = get_object_or_404(Comment, id=object_id)
    else:
        messages.error(request, "Invalid content type.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.recipe_post = recipe
            report.comment = comment
            report.save()
            messages.success(request, "Thank you. The content has been reported to administrators.")
            
            # --- FIX STARTS HERE ---
            # Use 'recipe_detail' (the name in urls.py) and 'post_id' (the url parameter)
            if recipe:
                return redirect('recipe_detail', post_id=recipe.id)
            else:
                return redirect('recipe_detail', post_id=comment.recipe_post.id)
            # --- FIX ENDS HERE ---

    else:
        form = ReportForm()

    return render(request, 'content/report_content.html', {
        'form': form, 
        'content_type': content_type, 
        'object': recipe or comment
    })
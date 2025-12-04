from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from recipes.models import RecipePost, Comment
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
            
            # Redirect back to the recipe page
            if recipe:
                return redirect('post_detail', pk=recipe.id) # Assuming you have this url
            else:
                return redirect('post_detail', pk=comment.recipe_post.id)
    else:
        form = ReportForm()

    return render(request, 'report_content.html', {
        'form': form, 
        'content_type': content_type, 
        'object': recipe or comment
    })
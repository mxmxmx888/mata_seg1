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
    recipe, comment = _get_report_target(content_type, object_id)
    if not (recipe or comment):
        messages.error(request, "Invalid content type.")
        return redirect('dashboard')

    if request.method == 'POST':
        redirect_response, form = _handle_report_post(request, recipe, comment)
        if redirect_response:
            return redirect_response
    else:
        form = ReportForm()

    return render(request, 'content/report_content.html', {
        'form': form, 
        'content_type': content_type, 
        'object': recipe or comment
    })


def _get_report_target(content_type, object_id):
    """Identify the object being reported; return (recipe, comment) pair."""
    if content_type == 'recipe':
        return get_object_or_404(RecipePost, id=object_id), None
    if content_type == 'comment':
        return None, get_object_or_404(Comment, id=object_id)
    return None, None


def _handle_report_post(request, recipe, comment):
    """Process POST to create a report; return (redirect_response, form)."""
    form = ReportForm(request.POST)
    if not form.is_valid():
        return None, form

    report = form.save(commit=False)
    report.reporter = request.user
    report.recipe_post = recipe
    report.comment = comment
    report.save()
    messages.success(request, "Thank you. The content has been reported to administrators.")

    if recipe:
        return redirect('recipe_detail', post_id=recipe.id), form
    return redirect('recipe_detail', post_id=comment.recipe_post.id), form

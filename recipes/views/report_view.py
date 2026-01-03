from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from recipes.forms.report_form import ReportForm
from recipes.services.reporting import ReportingService

reporting_service = ReportingService()

@login_required
def report_content(request, content_type, object_id):
    """
    Generic view to report either a recipe or a comment.
    content_type should be 'recipe' or 'comment'.
    """
    recipe, comment = reporting_service.report_for(content_type, object_id)
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
    return reporting_service.report_for(content_type, object_id)


def _handle_report_post(request, recipe, comment):
    """Process POST to create a report; return (redirect_response, form)."""
    form = ReportForm(request.POST)
    if not form.is_valid():
        return None, form

    reporting_service.save_report(form, request.user, recipe=recipe, comment=comment)
    messages.success(request, "Thank you. The content has been reported to administrators.")

    if recipe:
        return redirect('recipe_detail', post_id=recipe.id), form
    return redirect('recipe_detail', post_id=comment.recipe_post.id), form

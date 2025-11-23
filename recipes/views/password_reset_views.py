from django.conf import settings
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView
from recipes.forms import PasswordResetRequestForm
from recipes.views.decorators import LoginProhibitedMixin


class PasswordResetRequestView(LoginProhibitedMixin, FormView):
    """
    Collect the user's email address to start a password reset flow.

    The form intentionally behaves the same regardless of whether an account
    exists to avoid leaking user existence.
    """

    template_name = 'password_reset_request.html'
    form_class = PasswordResetRequestForm
    success_url = reverse_lazy('password_reset_done')
    redirect_when_logged_in_url = settings.REDIRECT_URL_WHEN_LOGGED_IN

    def form_valid(self, form):
        """
        Accept the email and proceed to the confirmation step.

        Hook for future email delivery can be added here without changing
        the user-facing flow.
        """

        return super().form_valid(form)


class PasswordResetDoneView(LoginProhibitedMixin, TemplateView):
    """Show a neutral confirmation after a reset request is submitted."""

    template_name = 'password_reset_done.html'
    redirect_when_logged_in_url = settings.REDIRECT_URL_WHEN_LOGGED_IN

from django.contrib.auth import login as auth_login
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic.edit import FormView

from recipes.forms import SignUpForm
from recipes.views.decorators import LoginProhibitedMixin
from recipes.firebase_admin_client import ensure_firebase_user


class SignUpView(LoginProhibitedMixin, FormView):
    """
    Handles user registration via the custom SignUpForm.
    """

    template_name = "auth/sign_up.html"
    form_class = SignUpForm
    success_url = reverse_lazy("dashboard")
    redirect_when_logged_in_url = reverse_lazy("dashboard")

    def get(self, request, *args, **kwargs):
        """Render the signup form."""
        form = self.form_class()
        return render(request, self.template_name, {"form": form})

    def form_valid(self, form):
        """Create user, ensure Firebase account, log in, and redirect."""
        user = form.save()

        ensure_firebase_user(
            email=user.email,
            display_name=user.get_full_name() or user.username,
        )

        auth_login(
            self.request,
            user,
            backend="django.contrib.auth.backends.ModelBackend",
        )

        return redirect(self.get_success_url())

    def form_invalid(self, form):
        """Re-render the signup form with errors."""
        return render(self.request, self.template_name, {"form": form})

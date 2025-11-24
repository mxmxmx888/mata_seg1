# recipes/views/log_in_view.py
from django.contrib.auth import login as auth_login
from django.shortcuts import redirect, render
from django.views.generic import View

from recipes.forms import LogInForm
from recipes.views.decorators import LoginProhibitedMixin


class LogInView(LoginProhibitedMixin, View):
    """
    Username + password login.

    - Uses LogInForm.get_user(), which first tries Firebase,
      then falls back to Django's password check.
    - On success, logs in via the ModelBackend and redirects to `dashboard`
      (or the ?next= URL if provided).
    """

    template_name = "log_in.html"

    def dispatch(self, request, *args, **kwargs):
        # Capture ?next=/some/url so we can redirect there after login
        self.next = request.GET.get("next") or request.POST.get("next")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = LogInForm()
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "next": self.next,
            },
        )

    def post(self, request, *args, **kwargs):
        form = LogInForm(request.POST)

        if form.is_valid():
            user = form.get_user()
            if user is not None:
                auth_login(
                    request,
                    user,
                    backend="django.contrib.auth.backends.ModelBackend",
                )
                return redirect(self.next or "dashboard")

        # If we get here, login failed
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "next": self.next,
            },
        )

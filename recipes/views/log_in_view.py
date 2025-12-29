from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.contrib.auth import login
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.contrib import messages
from recipes.forms.log_in_form import LogInForm
from recipes.views.decorators import LoginProhibitedMixin

@method_decorator(never_cache, name="dispatch")
class LogInView(LoginProhibitedMixin, View):
    """Display and process the login form for unauthenticated users."""
    
    redirect_when_logged_in_url = 'log_out'

    def dispatch(self, request, *args, **kwargs):
        """Capture ?next param before handling request."""
        self.next = request.POST.get("next") or request.GET.get("next") or None
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        """Render the login form."""
        form = LogInForm()
        return render(request, "auth/log_in.html", {"form": form, "next": self.next})

    def post(self, request):
        """Process login form submission."""
        form = LogInForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            if user:
                return self._login_success(request, user)
            form.add_error(None, self._error_message())
        messages.add_message(request, messages.ERROR, self._error_message())
        return render(request, "auth/log_in.html", {"form": form, "next": self.next})

    def _login_success(self, request, user):
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.add_message(request, messages.SUCCESS, "You have logged in successfully!")
        next_url = self.next or reverse("dashboard")
        if next_url == "None":
            next_url = reverse("dashboard")
        return redirect(next_url)

    def _error_message(self):
        return "Oh no, perhaps your username or password is incorrect!"

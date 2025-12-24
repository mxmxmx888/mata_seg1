from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.contrib.auth import login
from django.views import View
from django.contrib import messages
from recipes.forms.log_in_form import LogInForm
from recipes.views.decorators import LoginProhibitedMixin

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
            if user is not None:
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                
                messages.add_message(request, messages.SUCCESS, "You have logged in successfully!")

                next_url = self.next
                if not next_url or next_url == "None":
                    next_url = reverse("dashboard")

                return redirect(next_url)

        error_message = "Oh no, perhaps your username or password is incorrect!"
        if form.is_valid():
            form.add_error(None, error_message)
        messages.add_message(request, messages.ERROR, error_message)
        return render(request, "auth/log_in.html", {"form": form, "next": self.next})

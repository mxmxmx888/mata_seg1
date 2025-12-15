from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.contrib.auth import login
from django.views import View
from django.contrib import messages
from recipes.forms.log_in_form import LogInForm
from recipes.views.decorators import LoginProhibitedMixin

class LogInView(LoginProhibitedMixin, View):
    """
    Display the login form and handle the login action.
    """
    redirect_when_logged_in_url = reverse_lazy('dashboard')

    def dispatch(self, request, *args, **kwargs):
        self.next = request.POST.get("next") or request.GET.get("next") or None
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        form = LogInForm()
        return render(request, "auth/log_in.html", {"form": form, "next": self.next})

    def post(self, request):
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

        messages.add_message(request, messages.ERROR, "The credentials provided were invalid!")
        return render(request, "auth/log_in.html", {"form": form, "next": self.next})
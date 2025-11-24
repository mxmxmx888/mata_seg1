# recipes/views/log_in_view.py

from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth import login
from django.views import View

from recipes.forms.log_in_form import LogInForm
from recipes.views.decorators import LoginProhibitedMixin


class LogInView(LoginProhibitedMixin, View):
    def dispatch(self, request, *args, **kwargs):
        # store ?next= from GET or POST
        self.next = request.POST.get("next") or request.GET.get("next") or None
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        form = LogInForm()
        return render(request, "log_in.html", {"form": form, "next": self.next})

    def post(self, request):
        form = LogInForm(request.POST)

        if form.is_valid():
            user = form.get_user()
            if user is not None:
                login(request, user)

                # clean up the next URL
                next_url = self.next
                if not next_url or next_url == "None":
                    next_url = reverse("dashboard")

                return redirect(next_url)

        # if invalid, re-render form
        return render(request, "log_in.html", {"form": form, "next": self.next})

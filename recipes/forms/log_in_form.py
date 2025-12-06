from django import forms
from django.contrib.auth import authenticate   # <- add this
from recipes.models import User
from recipes.firebase_auth_services import sign_in_with_email_and_password


class LogInForm(forms.Form):
    username = forms.CharField(label="Username")
    password = forms.CharField(label="Password", widget=forms.PasswordInput())

    def get_user(self):
        user = None
        if self.is_valid():
            username = self.cleaned_data.get('username')
            password = self.cleaned_data.get('password')

            if not username or not password:
                return None

            try:
                django_user = User.objects.get(username=username)
            except User.DoesNotExist:
                print("DEBUG: No Django user with that username")
                return None

            # 1) Try Firebase first
            firebase_result = sign_in_with_email_and_password(
                email=django_user.email,
                password=password,
            )

            if firebase_result is not None:
                print("DEBUG: Firebase login succeeded")
                user = django_user
            else:
                print("DEBUG: Firebase login FAILED, trying Django authenticate()")
                # 2) Fallback: use Django auth so we can at least log in
                user = authenticate(username=username, password=password)

        print("DEBUG: get_user returning:", user)
        return user

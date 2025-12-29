from django import forms
from django.contrib.auth import authenticate
from recipes.models import User
from recipes.firebase_auth_services import sign_in_with_email_and_password
from recipes.firebase_admin_client import _is_running_tests


class LogInForm(forms.Form):
    """Authenticate a user by username/password against Firebase/Django backends."""
    username = forms.CharField(label="Username")
    password = forms.CharField(label="Password", widget=forms.PasswordInput())

    def get_user(self):
        """Return the authenticated user or None after validating credentials."""
        if not self.is_valid():
            return None

        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if not username or not password:
            return None

        user = self._get_django_user(username)
        if not user:
            return None

        authed = self._authenticate_with_firebase(user, password) or self._authenticate_with_django(
            username, password
        )
        self._log_debug(f"get_user returning: {authed}")
        return authed

    def _authenticate_with_firebase(self, user, password):
        result = sign_in_with_email_and_password(email=user.email, password=password)
        if result is None:
            self._log_debug("Firebase login FAILED, trying Django authenticate()")
            return None
        self._log_debug("Firebase login succeeded")
        user.backend = "django.contrib.auth.backends.ModelBackend"
        return user

    def _authenticate_with_django(self, username, password):
        return authenticate(username=username, password=password)

    def _get_django_user(self, username):
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            self._log_debug("No Django user with that username")
            return None

    def _log_debug(self, message: str):
        if not _is_running_tests():
            print(f"DEBUG: {message}")

# recipes/forms.py
from django import forms
from django.core.exceptions import ValidationError

from recipes.models import User
from recipes.firebase_auth_services import sign_in_with_email_and_password


class SignUpForm(forms.ModelForm):
    """
    Sign-up form for Django + Firebase.
    """
    password = forms.CharField(widget=forms.PasswordInput())
    password_confirmation = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        model = User
        fields = ("first_name", "last_name", "username", "email")

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password")
        p2 = cleaned.get("password_confirmation")

        if p1 and p2 and p1 != p2:
            self.add_error("password_confirmation", "Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class LogInForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput())

    def get_user(self):
        if not self.is_valid():
            return None

        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if not username or not password:
            return None

        # Django DB lookup
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return None

        # Try Firebase login first
        firebase_ok = sign_in_with_email_and_password(
            email=user.email,
            password=password,
        )

        if firebase_ok is not None:
            return user

        # Fall back to local Django password
        if user.check_password(password):
            return user

        return None

"""Forms for user profile editing, signup, and password changes."""

from django import forms
from django.contrib.auth import authenticate
from django.core.validators import RegexValidator
from recipes.models import User
from recipes.firebase_auth_services import create_firebase_user

class AvatarFileInput(forms.FileInput):
    """Custom widget for avatar uploads."""
    template_name = "widgets/avatar_file_input.html"

class UserForm(forms.ModelForm):
    """Form to update user profile information."""
    avatar = forms.ImageField(required=False, widget=AvatarFileInput())
    remove_avatar = forms.BooleanField(required=False, widget=forms.HiddenInput())
    bio = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.Textarea(attrs={"rows": 3, "style": "resize: none;"}),
        label="Profile description",
    )

    class Meta:
        """Model/field config for user profile form."""
        model = User
        fields = ['first_name', 'last_name', 'username', 'bio', 'email', 'is_private', 'avatar']
        labels = {
            'is_private': 'Private account',
        }

    def save(self, commit=True):
        """Save user profile updates, handling avatar removal/replacement."""
        existing_avatar = self.instance.avatar if self.instance and self.instance.pk else None
        user = super().save(commit=False)
        remove_avatar = self.cleaned_data.get('remove_avatar')
        new_avatar = self.cleaned_data.get('avatar')

        user.avatar = self._resolve_avatar(existing_avatar, new_avatar, remove_avatar)

        if commit:
            user.save()
        return user

    def _delete_avatar(self, avatar_file):
        if avatar_file:
            avatar_file.delete(save=False)

    def _replace_avatar(self, existing_avatar, new_avatar):
        if existing_avatar and existing_avatar != new_avatar:
            self._delete_avatar(existing_avatar)

    def _resolve_avatar(self, existing_avatar, new_avatar, remove_avatar):
        if remove_avatar:
            self._delete_avatar(existing_avatar)
            return None
        if new_avatar:
            self._replace_avatar(existing_avatar, new_avatar)
            return new_avatar
        return existing_avatar

class NewPasswordMixin(forms.Form):
    """Mixin providing password and password confirmation fields."""
    new_password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(),
        validators=[
            RegexValidator(
                regex=r'^(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9]).*$',
                message=(
                    'Password must contain an uppercase character, '
                    'a lowercase character, and a number'
                )
            )
        ]
    )
    password_confirmation = forms.CharField(label='Password confirmation', widget=forms.PasswordInput())

    def clean(self):
        """Validate new password and confirmation match."""
        super().clean()
        new_password = self.cleaned_data.get('new_password')
        password_confirmation = self.cleaned_data.get('password_confirmation')
        if new_password != password_confirmation:
            self.add_error(
                'password_confirmation', 
                'Confirmation does not match password.'
            )

class PasswordForm(NewPasswordMixin):
    """Form to validate current password and set a new one for a user."""
    password = forms.CharField(label='Current password', widget=forms.PasswordInput())

    def __init__(self, user=None, **kwargs):  
        """Store the target user for password validation."""
        super().__init__(**kwargs)
        self.user = user

    def clean(self):
        """Validate current password and new password confirmation."""
        super().clean()
        password = self.cleaned_data.get('password')
        if self.user is not None:
            user = authenticate(username=self.user.username, password=password)
        else:
            user = None
        if user is None:
            self.add_error('password', "Password is invalid")

    def save(self):
        """Update the user's password with the validated new password."""
        new_password = self.cleaned_data['new_password']
        if self.user is not None:
            self.user.set_password(new_password)
            self.user.save()
        return self.user

class SignUpForm(NewPasswordMixin, forms.ModelForm):
    """Form to register a new user with Django and Firebase."""
    class Meta:
        """Model/field config for signup form."""
        model = User
        fields = ['first_name', 'last_name', 'username', 'email']

    def save(self):
        """Create and return a new User in Django and Firebase."""
        super().save(commit=False)

        username = self.cleaned_data.get('username')
        first_name = self.cleaned_data.get('first_name')
        last_name = self.cleaned_data.get('last_name')
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('new_password')

        user = User.objects.create_user(
            username,
            first_name = first_name,
            last_name = last_name,
            email = email,
            password = password,
        )

        try:
            create_firebase_user(uid = username, email = email, password = password)
        except Exception:
            pass
        
        return user

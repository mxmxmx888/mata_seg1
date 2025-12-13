from django import forms
from django.contrib.auth import authenticate
from django.core.validators import RegexValidator
from recipes.models import User
from recipes.firebase_auth_services import create_firebase_user

class AvatarFileInput(forms.FileInput):
    template_name = "widgets/avatar_file_input.html"

class UserForm(forms.ModelForm):

    # Form to update user profile information.
    avatar = forms.ImageField(required=False, widget=AvatarFileInput())
    remove_avatar = forms.BooleanField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'is_private', 'avatar']
        labels = {
            'is_private': 'Private account',
        }

    def save(self, commit=True):
        existing_avatar = self.instance.avatar if self.instance and self.instance.pk else None
        user = super().save(commit=False)
        remove_avatar = self.cleaned_data.get('remove_avatar')
        new_avatar = self.cleaned_data.get('avatar')

        if remove_avatar:
            if existing_avatar:
                existing_avatar.delete(save=False)
            user.avatar = None
        elif new_avatar:
            if existing_avatar and existing_avatar != new_avatar:
                existing_avatar.delete(save=False)
            user.avatar = new_avatar
        else:
            user.avatar = existing_avatar

        # to not accidentally keep the initial file when clearing
        if remove_avatar:
            if existing_avatar:
                existing_avatar.delete(save=False)
            user.avatar = None

        if commit:
            user.save()
        return user

class NewPasswordMixin(forms.Form):
    #form mixin providing password and password confirmation fields.
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
        super().clean()
        new_password = self.cleaned_data.get('new_password')
        password_confirmation = self.cleaned_data.get('password_confirmation')
        if new_password != password_confirmation:
            self.add_error(
                'password_confirmation', 
                'Confirmation does not match password.'
            )


class PasswordForm(NewPasswordMixin):
    #Form enabling authenticated users to change their password.
    password = forms.CharField(label='Current password', widget=forms.PasswordInput())

    def __init__(self, user=None, **kwargs):  
        super().__init__(**kwargs)
        self.user = user

    def clean(self):

        #validating the current and new password fields.
        super().clean()
        password = self.cleaned_data.get('password')
        if self.user is not None:
            user = authenticate(username=self.user.username, password=password)
        else:
            user = None
        if user is None:
            self.add_error('password', "Password is invalid")

    def save(self):
        #Update the user's password with the new validated password.
        new_password = self.cleaned_data['new_password']
        if self.user is not None:
            self.user.set_password(new_password)
            self.user.save()
        return self.user


class SignUpForm(NewPasswordMixin, forms.ModelForm):

    # Form enabling new users to register for an account.
    class Meta:
        """Form options."""

        model = User
        fields = ['first_name', 'last_name', 'username', 'email']

    def save(self):
        #Create and return a new User instance.
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

"""Custom user model with profile metadata and avatar helpers."""

from django.core.validators import RegexValidator, MaxLengthValidator
from django.contrib.auth.models import AbstractUser
from django.db import models
from libgravatar import Gravatar
from django.templatetags.static import static

class User(AbstractUser):
    """Model for user auth, and team member related info"""

    username = models.CharField(
        max_length=30,
        unique=True,
        validators=[RegexValidator(
            regex=r'^\w{3,}$',
            message='Username must consist of at least three alphanumericals'
        )]
    )
    first_name = models.CharField(max_length=50, blank=False)
    last_name = models.CharField(max_length=50, blank=False)
    email = models.EmailField(unique=True, blank=False)
    bio = models.TextField(
        max_length=500,
        blank=True,
        help_text="short user bio shown on profile",
        validators=[MaxLengthValidator(500)]
    )
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_private = models.BooleanField(default=False)

    class Meta:
        """Default ordering for users."""
        ordering = ['last_name', 'first_name']

    def full_name(self):
        """Return full name string."""
        return f'{self.first_name} {self.last_name}'

    def gravatar(self, size=120):
        """Return gravatar URL for the user's email."""
        gravatar_object = Gravatar(self.email)
        gravatar_url = gravatar_object.get_image(size=size, default='mp')
        return gravatar_url

    def mini_gravatar(self):
        """Return smaller gravatar URL."""
        return self.avatar_or_gravatar(size=60)

    def avatar_or_gravatar(self, size=120):
        """Return uploaded avatar URL or a default gravatar fallback."""
        if self.avatar:
            try:
                return self.avatar.url
            except ValueError:
                pass
        return static("img/default-avatar.svg")

    @property
    def avatar_url(self):
        """Preferred avatar URL for profile display."""
        return self.avatar_or_gravatar(size=200)

    @property
    def mini_avatar_url(self):
        """Preferred small avatar URL for compact UI."""
        return self.avatar_or_gravatar(size=60)

    def save(self, *args, **kwargs):
        """
        Override the save method to handle the 'remove_avatar' flag.
        """
        if kwargs.pop('remove_avatar', False):
            self.avatar = None
        super().save(*args, **kwargs)

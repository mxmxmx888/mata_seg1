from django.core.validators import RegexValidator
from django.contrib.auth.models import AbstractUser
from django.db import models
from libgravatar import Gravatar

class User(AbstractUser):
    """Model for user auth, and team member related info"""

    username = models.CharField(
        max_length=30,
        unique=True,
        validators=[RegexValidator(
            regex=r'^\w{3,}$',
            message='Username must consist of @ followed by at least three alphanumericals'
        )]
    )
    first_name = models.CharField(max_length=50, blank=False)
    last_name = models.CharField(max_length=50, blank=False)
    email = models.EmailField(unique=True, blank=False)
    bio = models.TextField(
        max_length=500,
        blank=True,
        help_text="short user bio shown on profile"
    )
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    def gravatar(self, size=120):
        """Return a URL to the user's gravatar."""
        gravatar_object = Gravatar(self.email)
        gravatar_url = gravatar_object.get_image(size=size, default='mp')
        return gravatar_url

    def mini_gravatar(self):
        return self.avatar_or_gravatar(size=60)

    def avatar_or_gravatar(self, size=120):
        if self.avatar:
            try:
                return self.avatar.url
            except ValueError:
                pass
        return self.gravatar(size=size)

    @property
    def avatar_url(self):
        return self.avatar_or_gravatar(size=200)

    @property
    def mini_avatar_url(self):
        return self.avatar_or_gravatar(size=60)

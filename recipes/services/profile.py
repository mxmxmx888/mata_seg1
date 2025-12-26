"""Service helpers for deriving user avatar URLs in different contexts."""

class ProfileDisplayService:
    """Provide avatar URLs for profile editing and navbar contexts."""
    def __init__(self, user):
        """Bind the service to a user instance."""
        self.user = user

    def _user_avatar(self):
        """Return the best available avatar URL or blank when unauthenticated."""
        if not self.user or not getattr(self.user, "is_authenticated", False):
            return ""
        return getattr(self.user, "avatar_url", "") or ""

    def editing_avatar_url(self):
        """Return avatar URL used in profile editing contexts."""
        return self._user_avatar()

    def navbar_avatar_url(self):
        """Return avatar URL used in navbar display."""
        return self._user_avatar()

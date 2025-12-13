class ProfileDisplayService:
    def __init__(self, user):
        self.user = user

    def _user_avatar(self):
        if not self.user or not getattr(self.user, "is_authenticated", False):
            return ""
        return getattr(self.user, "avatar_url", "") or ""

    def editing_avatar_url(self):
        return self._user_avatar()

    def navbar_avatar_url(self):
        return self._user_avatar()

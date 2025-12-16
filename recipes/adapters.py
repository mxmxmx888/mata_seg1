import re
from allauth.account.adapter import DefaultAccountAdapter

class CustomAccountAdapter(DefaultAccountAdapter):
    def clean_username(self, username, shallow=False):
        username = username or ""
        username = username.strip().lower()
        username = username.replace(" ", ".")
        username = username.replace("-", ".")
        username = re.sub(r"[^a-z0-9_.]", "", username)
        username = re.sub(r"[.]{2,}", ".", username)
        username = re.sub(r"[_]{2,}", "_", username)
        username = username.strip("._")

        if not username:
            username = "user"

        max_len = getattr(self, "get_username_max_length", lambda: 150)()
        username = username[:max_len]

        return username

    def populate_username(self, request, user):
        try:
            username = super().populate_username(request, user)
            if username:
                user.username = self.clean_username(username)
                return user.username
        except NotImplementedError:
            pass

        base = ""
        if getattr(user, "username", None):
            base = user.username
        elif getattr(user, "email", None):
            base = user.email.split("@")[0]
        elif getattr(user, "first_name", None):
            base = user.first_name
        else:
            base = "user"

        base = self.clean_username(base)

        UserModel = type(user)
        username = base
        counter = 1

        while UserModel.objects.filter(username=username).exists():
            suffix = str(counter)
            cut = max(1, len(base) - len(suffix))
            username = f"{base[:cut]}{suffix}"
            counter += 1

        user.username = username
        return user.username
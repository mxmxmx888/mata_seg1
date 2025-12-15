import re
from allauth.account.adapter import DefaultAccountAdapter


class CustomAccountAdapter(DefaultAccountAdapter):
    def clean_username(self, username, shallow=False):
        """
        Allow usernames without '@'. Only allow letters, digits, underscore, dot.
        If invalid, raise ValueError to trigger form errors.
        """
        if username.startswith("@"):
            username = username[1:]
        if not re.match(r"^[a-zA-Z0-9_.]+$", username):
            raise ValueError("Username must contain only letters, numbers, underscores, or dots.")
        return username

    def populate_username(self, request, user):
        """
        Deterministic username generation:
        - If user.username exists -> clean and use it.
        - Else use email local-part / first_name / 'user'
        - If collision -> append 1,2,3... (so 'test' -> 'test1')
        """
        UserModel = type(user)

        base = (user.username or "").strip()
        if base:
            base = base.lstrip("@")
        else:
            email = (getattr(user, "email", "") or "").strip()
            if email and "@" in email:
                base = email.split("@", 1)[0]
            else:
                base = (getattr(user, "first_name", "") or "").strip() or "user"

        base = base.lstrip("@")
        base = re.sub(r"[^a-zA-Z0-9_.]", "", base).lower() or "user"

        username = base
        if UserModel.objects.filter(username=username).exists():
            counter = 1
            while UserModel.objects.filter(username=f"{base}{counter}").exists():
                counter += 1
            username = f"{base}{counter}"

        return username
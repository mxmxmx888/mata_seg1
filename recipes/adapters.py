from allauth.account.adapter import DefaultAccountAdapter


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom adapter to make sure social logins always get a valid username
    for our custom User model.
    """

    def populate_username(self, request, user):
        """
        Try the default behaviour first. If allauth can't find a unique
        username and raises NotImplementedError, fall back to our own
        simple strategy.
        """
        try:
            return super().populate_username(request, user)
        except NotImplementedError:
            base = ""

            if user.username:
                base = user.username
            elif getattr(user, "email", None):
                base = user.email.split("@")[0]
            elif getattr(user, "first_name", None):
                base = user.first_name
            else:
                base = "user"

            base = base.replace(" ", "").lower() or "user"

            UserModel = type(user)
            username = base
            counter = 1

            while UserModel.objects.filter(username=username).exists():
                username = f"{base}{counter}"
                counter += 1

            user.username = username
            return user.username

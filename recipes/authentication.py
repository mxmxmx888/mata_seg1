from rest_framework import authentication, exceptions
from firebase_admin import auth as firebase_auth
from .firebase import *
from django.contrib.auth.models import User


class FirebaseAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')

        if not auth_header:
            return None

        parts = auth_header.split()

        if len(parts) != 2 or parts[0].lower() != 'bearer':
            raise exceptions.AuthenticationFailed("Invalid Authorization header")

        id_token = parts[1]

        try:
            decoded_token = firebase_auth.verify_id_token(id_token)
        except Exception:
            raise exceptions.AuthenticationFailed("Invalid or expired token")

        uid = decoded_token.get("uid")
        email = decoded_token.get("email", "")

        user, created = User.objects.get_or_create(
            username=uid,
            defaults={"email": email},
        )

        return (user, None)

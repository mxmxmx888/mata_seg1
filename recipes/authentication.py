import os
import firebase_admin
from firebase_admin import auth
from django.contrib.auth import get_user_model
from rest_framework import authentication
from rest_framework import exceptions
from .firebase_admin_client import get_app

User = get_user_model()

class FirebaseAuthentication(authentication.BaseAuthentication):
    """DRF authentication backend validating Firebase ID tokens."""

    def authenticate(self, request):
        """Validate Authorization header token and return (user, auth)."""
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None

        id_token = auth_header.split(' ').pop()
        
        try:
            get_app()
            decoded_token = auth.verify_id_token(id_token)
        except Exception:
            raise exceptions.AuthenticationFailed('Invalid Firebase token')

        try:
            uid = decoded_token.get("uid")
            user = User.objects.get(username=uid) 
            return (user, None)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('User not found')

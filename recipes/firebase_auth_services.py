import requests
from django.conf import settings
from firebase_admin import auth as firebase_auth
from .firebase_admin_client import get_app


def create_firebase_user(uid: str, email: str, password: str):
    """
    Create a user in Firebase Auth with given uid, email and password.
    """
    get_app()  # ensure Firebase app is initialised
    user = firebase_auth.create_user(
        uid=uid,
        email=email,
        password=password,
    )
    return user


def sign_in_with_email_and_password(email: str, password: str):
    api_key = getattr(settings, "FIREBASE_API_KEY", None)
    if not api_key:
        print("DEBUG: No FIREBASE_API_KEY configured in settings")
        return None

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        print("DEBUG: Firebase sign-in OK for", email)
        return response.json()

    print("DEBUG: Firebase sign-in FAILED")
    print("DEBUG: Status:", response.status_code)
    print("DEBUG: Body:", response.text)
    return None

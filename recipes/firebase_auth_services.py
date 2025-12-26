"""Firebase Auth helper functions used by server-side flows."""

import logging
import requests
from django.conf import settings
from firebase_admin import auth as firebase_auth
from .firebase_admin_client import get_app, _is_running_tests

logger = logging.getLogger(__name__)


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
    """Sign in against Firebase REST API; return response JSON or None."""
    # Avoid real network calls during most test runs unless the HTTP client is mocked.
    is_test_run = _is_running_tests()
    if is_test_run:
        try:
            is_mocked = "unittest.mock" in type(requests.post).__module__
        except Exception:
            is_mocked = False
        if not is_mocked:
            return None

    api_key = getattr(settings, "FIREBASE_API_KEY", None)
    if not api_key:
        if not is_test_run:
            message = "Firebase sign-in skipped: FIREBASE_API_KEY not configured"
            print(message)
            logger.warning(message)
        return None

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        if not is_test_run:
            message = f"Firebase sign-in OK for {email}"
            print(message)
            logger.debug(message)
        return response.json()

    if not is_test_run:
        body = getattr(response, "text", "")
        print("Firebase sign-in failed")
        print(f"status={response.status_code}")
        print(f"body={body}")
        logger.warning(
            "Firebase sign-in failed for %s (status=%s, body=%s)",
            email,
            response.status_code,
            body,
        )
    return None


def generate_password_reset_link(email: str):
    """
    Generate a password reset link for the given email using Firebase Admin SDK.
    """
    is_test_run = _is_running_tests()
    get_app()
    try:
        link = firebase_auth.generate_password_reset_link(email)
        return link
    except firebase_auth.UserNotFoundError:
        if not is_test_run:
            message = f"Firebase user not found for password reset: {email}"
            print(message)
            logger.info(message)
        return None
    except Exception as e:
        if not is_test_run:
            message = f"Error generating Firebase password reset link: {e}"
            print(message)
            logger.warning(message)
        return None

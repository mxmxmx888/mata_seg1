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

def _requests_call_mocked():
    """Check if requests.post is currently mocked (for testing)."""
    try:
        return "unittest.mock" in type(requests.post).__module__
    except Exception:
        return False

def _get_api_key(is_test_run: bool):
    """Retrieve Firebase API key from settings, with logging if missing."""
    api_key = getattr(settings, "FIREBASE_API_KEY", None)
    if api_key or is_test_run:
        return api_key
    message = "Firebase sign-in skipped: FIREBASE_API_KEY not configured"
    print(message)
    logger.warning(message)
    return None

def _log_sign_in_failure(email, response):
    """Log Firebase sign-in failure details including status and response body."""
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


def sign_in_with_email_and_password(email: str, password: str):
    """Sign in against Firebase REST API; return response JSON or None."""
    is_test_run = _is_running_tests()
    if is_test_run and not _requests_call_mocked():
        return None

    api_key = _get_api_key(is_test_run)
    if not api_key:
        return None

    response = requests.post(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}",
        json={"email": email, "password": password, "returnSecureToken": True},
    )

    if response.status_code == 200:
        if not is_test_run:
            print(f"Firebase sign-in OK for {email}")
            logger.debug("Firebase sign-in OK for %s", email)
        return response.json()

    if not is_test_run:
        _log_sign_in_failure(email, response)
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
        _log_missing_user(email, is_test_run)
        return None
    except Exception as e:
        _log_reset_error(e, is_test_run)
        return None


def _log_missing_user(email, is_test_run):
    """Log when a Firebase user is not found during password reset."""
    if is_test_run:
        return
    message = f"Firebase user not found for password reset: {email}"
    print(message)
    logger.info(message)


def _log_reset_error(error, is_test_run):
    """Log errors encountered while generating Firebase password reset link."""
    if is_test_run:
        return
    message = f"Error generating Firebase password reset link: {error}"
    print(message)
    logger.warning(message)

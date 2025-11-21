import os
import firebase_admin
from firebase_admin import credentials, auth


_app = None


def get_app():
    """
    Lazily initialise the Firebase Admin app using the service account file.
    Safe against multiple imports / reloads.
    """
    global _app

    if _app is not None:
        return _app

    if firebase_admin._apps:
        _app = firebase_admin.get_app()
        return _app

    cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_FILE")
    if not cred_path:
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT_FILE is not set in environment/.env"
        )

    cred = credentials.Certificate(cred_path)
    _app = firebase_admin.initialize_app(cred)
    return _app


def ensure_firebase_user(email: str, display_name: str | None = None):
    """
    Ensure that a Firebase Auth user exists with this email.
    If it doesn't, create one.
    """
    if not email:
        return None

    get_app()

    try:
        user = auth.get_user_by_email(email)
    except auth.UserNotFoundError:
        user = auth.create_user(
            email=email,
            display_name=display_name,
        )
    return user

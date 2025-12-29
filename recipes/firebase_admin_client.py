"""Firebase Admin client helpers with test-safe behaviors."""

import logging
import os
import sys
import firebase_admin
from firebase_admin import credentials, auth, firestore

logger = logging.getLogger(__name__)

def _is_mock(obj) -> bool:
    """Return True when obj is a unittest.mock sentinel."""
    try:
        return "unittest.mock" in type(obj).__module__
    except Exception:
        return False

def _env_truthy(name: str, default: str = "false") -> bool:
    """Return True when env var is set to a truthy value."""
    return os.getenv(name, default).lower() in ("1", "true", "yes")

def _should_log() -> bool:
    """Silence noisy Firebase logs during tests unless explicitly enabled."""
    return not _is_running_tests() or _env_truthy("FIREBASE_VERBOSE_TEST_LOGS")

def _is_running_tests():
    """
    Return True when Django is executing the test suite.
    This prevents Firebase from attempting network calls during tests.
    """
    return any(arg in sys.argv for arg in ["test", "pytest"])

def _should_skip_app_init() -> bool:
    """Skip Firebase init during tests unless explicitly enabled or mocked."""
    if not _is_running_tests():
        return False
    if _env_truthy("FIREBASE_ALLOW_TEST_APP"):
        return False
    return not _is_mock(firebase_admin.initialize_app)

def _load_credential():
    cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_FILE")
    if not cred_path or not os.path.exists(cred_path):
        if _should_log():
            message = "FIREBASE_SERVICE_ACCOUNT_FILE not found. Firebase features disabled."
            print(message)
            logger.warning(message)
        return None
    return credentials.Certificate(cred_path)

def _init_app(cred):
    try:
        return firebase_admin.initialize_app(cred)
    except Exception as e:
        _log_init_failure(e)
        return None


def _log_init_failure(error):
    if not _should_log():
        return
    message = f"Failed to initialize Firebase: {error}"
    print(message)
    logger.error(message)

_app = None

def get_app():
    """
    Lazily initialise the Firebase Admin app.
    Returns None if credentials are missing or invalid, preventing crashes.
    """
    global _app
    if _app:
        return _app
    if firebase_admin._apps:
        _app = firebase_admin.get_app()
        return _app
    if _should_skip_app_init():
        return None

    cred = _load_credential()
    if not cred:
        return None

    _app = _init_app(cred)
    return _app

def get_firestore_client():
    """Helper to get Firestore client safely."""
    # Allow opting out entirely (useful for local dev/seed without Firestore).
    firebase_enabled = _env_truthy("FIREBASE_ENABLE_FIRESTORE", "true")
    if not firebase_enabled:
        return None
    # Skip Firestore entirely during test runs to avoid network calls.
    if _is_running_tests():
        return None
    app = get_app()
    if not app:
        return None
    return firestore.client()

def _auth_blocked_in_tests() -> bool:
    return _is_running_tests() and not _env_truthy("FIREBASE_ALLOW_TEST_AUTH")

def _auth_functions_mocked() -> bool:
    return _is_mock(auth.get_user_by_email) or _is_mock(auth.create_user)

def _fetch_user(email):
    try:
        return auth.get_user_by_email(email), True
    except auth.UserNotFoundError:
        return None, True
    except Exception as e:
        _log_connection_error(e)
        return None, False

def _create_firebase_user(email: str, display_name: str | None):
    try:
        return auth.create_user(email=email, display_name=display_name)
    except Exception as e:
        _log_user_creation_error(e)
        return None


def _log_connection_error(error):
    if not _should_log():
        return
    print(f"Firebase connection error: {error}")
    logger.error("Firebase connection error: %s", error)


def _log_user_creation_error(error):
    if not _should_log():
        return
    print(f"Error creating Firebase user: {error}")
    logger.error("Error creating Firebase user: %s", error)

def ensure_firebase_user(email: str, display_name: str | None = None):
    """
    Ensure that a Firebase Auth user exists. Returns UserRecord or None.
    """
    if not email:
        return None
    if _auth_blocked_in_tests() and not _auth_functions_mocked():
        return None
    if not (_auth_functions_mocked() or get_app()):
        return None

    existing, allow_create = _fetch_user(email)
    if existing or not allow_create:
        return existing
    return _create_firebase_user(email, display_name)

import os
import sys
import firebase_admin
from firebase_admin import credentials, auth, firestore

def _is_mock(obj) -> bool:
    """Return True when obj is a unittest.mock sentinel."""
    try:
        return "unittest.mock" in type(obj).__module__
    except Exception:
        return False

def _env_truthy(name: str, default: str = "false") -> bool:
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

_app = None

def get_app():
    """
    Lazily initialise the Firebase Admin app.
    Returns None if credentials are missing or invalid, preventing crashes.
    """
    global _app

    # 1. If already active, return it
    if _app:
        return _app
    
    # 2. Check if initialized by another module
    if firebase_admin._apps:
        _app = firebase_admin.get_app()
        return _app

    # Avoid initializing during tests unless explicitly allowed or mocked.
    if _is_running_tests() and not _env_truthy("FIREBASE_ALLOW_TEST_APP"):
        if not _is_mock(firebase_admin.initialize_app):
            return None

    # 3. Try to initialize
    cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_FILE")
    
    if not cred_path or not os.path.exists(cred_path):
        # Log warning instead of raising RuntimeError to keep Django alive
        if _should_log():
            print("WARNING: FIREBASE_SERVICE_ACCOUNT_FILE not found. Firebase features disabled.")
        return None

    try:
        cred = credentials.Certificate(cred_path)
        _app = firebase_admin.initialize_app(cred)
        return _app
    except Exception as e:
        if _should_log():
            print(f"ERROR: Failed to initialize Firebase: {e}")
        return None

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

def ensure_firebase_user(email: str, display_name: str | None = None):
    """
    Ensure that a Firebase Auth user exists. Returns UserRecord or None.
    """
    if not email: 
        return None

    is_test = _is_running_tests()
    mocked_auth = _is_mock(auth.get_user_by_email) or _is_mock(auth.create_user)

    # Do not hit the network in tests unless mocked or explicitly allowed.
    if is_test and not _env_truthy("FIREBASE_ALLOW_TEST_AUTH"):
        if not mocked_auth:
            return None
        app = True  # Fake truthy app so downstream logic runs under mocks.
    else:
        app = get_app()
        if not app: 
            return None  # Fail silently
    
    try:
        return auth.get_user_by_email(email)
    except auth.UserNotFoundError:
        try:
            return auth.create_user(email=email, display_name=display_name)
        except Exception as e:
            if _should_log():
                print(f"Error creating Firebase user: {e}")
            return None
    except Exception as e:
        if _should_log():
            print(f"Firebase connection error: {e}")
        return None

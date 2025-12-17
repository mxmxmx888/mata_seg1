import os
import firebase_admin
from firebase_admin import credentials, auth, firestore

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

    # 3. Try to initialize
    cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_FILE")
    
    if not cred_path or not os.path.exists(cred_path):
        # Log warning instead of raising RuntimeError to keep Django alive
        print("WARNING: FIREBASE_SERVICE_ACCOUNT_FILE not found. Firebase features disabled.")
        return None

    try:
        cred = credentials.Certificate(cred_path)
        _app = firebase_admin.initialize_app(cred)
        return _app
    except Exception as e:
        print(f"ERROR: Failed to initialize Firebase: {e}")
        return None

def get_firestore_client():
    """Helper to get Firestore client safely."""
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
    
    app = get_app()
    if not app: 
        return None  # Fail silently

    try:
        return auth.get_user_by_email(email)
    except auth.UserNotFoundError:
        try:
            return auth.create_user(email=email, display_name=display_name)
        except Exception as e:
            print(f"Error creating Firebase user: {e}")
            return None
    except Exception as e:
        print(f"Firebase connection error: {e}")
        return None
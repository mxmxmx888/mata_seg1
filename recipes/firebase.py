import os
import firebase_admin
from firebase_admin import credentials
from django.conf import settings


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVICE_ACCOUNT_PATH = os.path.join(BASE_DIR, 'firebase-service-account.json')

cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_FILE", SERVICE_ACCOUNT_PATH)

# Initialize only if the credential file actually exists; otherwise leave
# initialization to firebase_admin_client.get_app().
if os.path.exists(cred_path) and not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

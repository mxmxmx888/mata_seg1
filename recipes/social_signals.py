import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver

from allauth.socialaccount.signals import social_account_added, social_account_updated
from google.api_core.exceptions import NotFound

from recipes.firebase_admin_client import (
    ensure_firebase_user,
    get_firestore_client,
    _is_running_tests,
    _env_truthy,
)

logger = logging.getLogger(__name__)
User = get_user_model()
_firestore_unavailable = False

def _should_log():
    """Decide whether to emit Firebase diagnostic logs."""
    return not _is_running_tests() or _env_truthy("FIREBASE_VERBOSE_TEST_LOGS")

def _display_name_for(user):
    full_name = ""
    if hasattr(user, "get_full_name"):
        full_name = (user.get_full_name() or "").strip()
    return full_name or (getattr(user, "username", "") or "").strip() or getattr(user, "email", "") or ""

def _sync_user_to_firebase(user, context):
    email = getattr(user, "email", None)
    if not email:
        return
    try:
        ensure_firebase_user(email=email, display_name=_display_name_for(user))
    except Exception as e:  # pragma: no cover - safety net
        _log_sync_warning(context, e)


def _log_sync_warning(context, error):
    if not _should_log():
        return
    logger.warning("Firebase sync (%s) failed: %s", context, error)


@receiver(social_account_added)
@receiver(social_account_updated)
def sync_google_user_to_firebase_on_social(sender, request, sociallogin, **kwargs):
    """
    allauth social signal handler signature MUST be:
    (sender, request, sociallogin, **kwargs)

    Sync a user's social account details to Firebase on add/update.
    """
    user = getattr(sociallogin, "user", None)
    if user:
        _sync_user_to_firebase(user, "social")


@receiver(user_logged_in)
def sync_user_to_firebase_on_login(sender, request, user, **kwargs):
    """Ensure a Firebase user exists on standard login."""
    _sync_user_to_firebase(user, "login")


@receiver(post_save, sender=User)
def sync_user_data_to_firestore(sender, instance, created, **kwargs):
    """
    Whenever the Django User model is saved, copy the data to Firestore.

    Skips when Firestore is unavailable; logs in verbose mode only when requested.
    """
    global _firestore_unavailable
    if _firestore_unavailable:
        return

    db = get_firestore_client()
    if db is None:
        return

    try:
        db.collection("users").document(str(instance.id)).set(_user_firestore_payload(instance), merge=True)
    except NotFound:
        _firestore_unavailable = True
        _log_firestore_missing()
    except Exception as e:
        _log_sync_error(e)

def _user_firestore_payload(instance):
    return {
        "username": instance.username,
        "email": instance.email,
        "is_staff": instance.is_staff,
        "date_joined": instance.date_joined,
        "id": instance.id,
    }

def _log_firestore_missing():
    if _should_log():  # pragma: no cover - defensive logging
        logger.warning(
            "Firestore database missing for project. Create it in GCP or set FIREBASE_ENABLE_FIRESTORE=false to disable syncing."
        )

def _log_sync_error(error):
    if _should_log():
        logger.warning("Error syncing to Firestore: %s", error)

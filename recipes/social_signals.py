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
    return not _is_running_tests() or _env_truthy("FIREBASE_VERBOSE_TEST_LOGS")  # pragma: no cover - diagnostic toggle only


@receiver(social_account_added)
@receiver(social_account_updated)
def sync_google_user_to_firebase_on_social(sender, request, sociallogin, **kwargs):
    """
    allauth social signal handler signature MUST be:
    (sender, request, sociallogin, **kwargs)
    """
    try:
        user = getattr(sociallogin, "user", None)
        if not user:
            return

        email = getattr(user, "email", None)
        if not email:
            return

        full_name = ""
        if hasattr(user, "get_full_name"):
            full_name = (user.get_full_name() or "").strip()

        display_name = full_name or (getattr(user, "username", "") or "").strip() or email

        ensure_firebase_user(email=email, display_name=display_name)

    except Exception as e:
        if _should_log():
            logger.warning("Firebase sync (social) failed: %s", e)


@receiver(user_logged_in)
def sync_user_to_firebase_on_login(sender, request, user, **kwargs):
    try:
        email = getattr(user, "email", None)
        if not email:
            return

        full_name = ""
        if hasattr(user, "get_full_name"):
            full_name = (user.get_full_name() or "").strip()

        display_name = full_name or (getattr(user, "username", "") or "").strip() or email

        ensure_firebase_user(email=email, display_name=display_name)

    except Exception as e:
        if _should_log():
            logger.warning("Firebase sync (login) failed: %s", e)


@receiver(post_save, sender=User)
def sync_user_data_to_firestore(sender, instance, created, **kwargs):
    """
    Whenever the Django User model is saved, copy the data to Firestore.
    """
    global _firestore_unavailable
    if _firestore_unavailable:
        return

    db = get_firestore_client()
    if db is None:
        return

    try:
        user_data = {
            "username": instance.username,
            "email": instance.email,
            "is_staff": instance.is_staff,
            "date_joined": instance.date_joined,
            "id": instance.id,
        }

        db.collection("users").document(str(instance.id)).set(user_data, merge=True)

    except NotFound:
        _firestore_unavailable = True
        if _should_log():  # pragma: no cover - defensive logging
            logger.warning(
                "Firestore database missing for project. Create it in GCP or set FIREBASE_ENABLE_FIRESTORE=false to disable syncing."
            )
    except Exception as e:
        if _should_log():
            logger.warning("Error syncing to Firestore: %s", e)

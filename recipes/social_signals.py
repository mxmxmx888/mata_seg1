from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from allauth.socialaccount.signals import social_account_added, social_account_updated

from .firebase_admin_client import ensure_firebase_user


@receiver(social_account_added)
@receiver(social_account_updated)
def sync_google_user_to_firebase_on_social(sender, request, sociallogin, **kwargs):
    """
    When a social account (e.g., Google) is added/updated,
    ensure the user exists in Firebase.
    """
    user = sociallogin.user
    email = getattr(user, "email", None)
    name = user.get_full_name() or getattr(user, "username", None)

    print(f"[SIGNAL social] social_account_* fired for email={email}, name={name}")

    if not email:
        print("[SIGNAL social] No email on user, skipping Firebase sync.")
        return

    try:
        ensure_firebase_user(email=email, display_name=name)
    except Exception as e:
        print("[SIGNAL social] Error while syncing to Firebase:", e)


@receiver(user_logged_in)
def sync_user_to_firebase_on_login(sender, request, user, **kwargs):
    """
    On ANY login (password or Google), ensure user is in Firebase.
    This catches existing Google accounts that were created before signals.
    """
    email = getattr(user, "email", None)
    name = user.get_full_name() or getattr(user, "username", None)

    print(f"[SIGNAL login] user_logged_in fired for email={email}, name={name}")

    if not email:
        print("[SIGNAL login] No email on user, skipping Firebase sync.")
        return

    try:
        ensure_firebase_user(email=email, display_name=name)
    except Exception as e:
        print("[SIGNAL login] Error while syncing to Firebase:", e)

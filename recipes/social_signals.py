from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from allauth.socialaccount.signals import social_account_added, social_account_updated

from .firebase_admin_client import ensure_firebase_user, get_firestore_client

@receiver(social_account_added)
@receiver(social_account_updated)
def sync_google_user_to_firebase_on_social(sender, request, sociallogin, **kwargs):
    user = sociallogin.user
    email = getattr(user, "email", None)
    name = user.get_full_name() or getattr(user, "username", None)

    if email:
        ensure_firebase_user(email=email, display_name=name)

@receiver(user_logged_in)
def sync_user_to_firebase_on_login(sender, request, user, **kwargs):
    email = getattr(user, "email", None)
    name = user.get_full_name() or getattr(user, "username", None)

    if email:
        ensure_firebase_user(email=email, display_name=name)

@receiver(post_save, sender=User)
def sync_user_data_to_firestore(sender, instance, created, **kwargs):
    """
    Whenever the Django User model is saved (by Admin, Registration, or Google Auth),
    copy the data to Firestore.
    """
    db = get_firestore_client()
    
    if db is None:
        return

    try:
        user_data = {
            'username': instance.username,
            'email': instance.email,
            'is_staff': instance.is_staff,
            'date_joined': instance.date_joined,
            'id': instance.id
        }
        
        db.collection('users').document(str(instance.id)).set(user_data, merge=True)
        print(f"Synced user {instance.id} to Firestore.")
        
    except Exception as e:
        print(f"Error syncing to Firestore: {e}")
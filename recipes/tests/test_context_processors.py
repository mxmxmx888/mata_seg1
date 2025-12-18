from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from recipes.context_processors import edit_profile_form, notifications
from recipes.models import Notification, Follower, FollowRequest
from recipes.tests.helpers import make_user


class EditProfileFormContextTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_returns_empty_for_anonymous_user(self):
        req = self.factory.get("/")
        req.user = AnonymousUser()

        self.assertEqual(edit_profile_form(req), {})

    @patch("recipes.context_processors.ProfileDisplayService")
    def test_returns_forms_and_avatar_urls(self, mock_display_service):
        user = make_user()
        req = self.factory.get("/")
        req.user = user

        mock_display_service.return_value.editing_avatar_url.return_value = "edit-url"
        mock_display_service.return_value.navbar_avatar_url.return_value = "nav-url"

        ctx = edit_profile_form(req)

        mock_display_service.assert_called_once_with(user)
        self.assertIn("edit_profile_form", ctx)
        self.assertIn("password_form", ctx)
        self.assertEqual(ctx["edit_profile_avatar_url"], "edit-url")
        self.assertEqual(ctx["navbar_avatar_url"], "nav-url")


class NotificationsContextTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.recipient = make_user(username="@me")
        self.pending_sender = make_user(username="@pending")
        self.follower_sender = make_user(username="@follower")

    def test_returns_empty_for_anonymous_user(self):
        req = self.factory.get("/")
        req.user = AnonymousUser()

        self.assertEqual(notifications(req), {})

    def test_filters_follow_notifications_and_counts_unread(self):
        req = self.factory.get("/")
        req.user = self.recipient

        # following_ids should include authors the user follows
        Follower.objects.create(follower=self.recipient, author=self.pending_sender)
        Follower.objects.create(follower=self.recipient, author=self.follower_sender)

        # Pending follow request notification (should remain)
        fr = FollowRequest.objects.create(
            requester=self.pending_sender,
            target=self.recipient,
            status=FollowRequest.STATUS_PENDING,
        )
        Notification.objects.create(
            recipient=self.recipient,
            sender=self.pending_sender,
            notification_type="follow_request",
            follow_request=fr,
        )

        # Follow from pending sender should be filtered out
        Notification.objects.create(
            recipient=self.recipient,
            sender=self.pending_sender,
            notification_type="follow",
        )

        # Two follow notifications from same sender -> should de-duplicate to one
        Notification.objects.create(
            recipient=self.recipient,
            sender=self.follower_sender,
            notification_type="follow",
            is_read=True,
        )
        Notification.objects.create(
            recipient=self.recipient,
            sender=self.follower_sender,
            notification_type="follow",
            is_read=False,
        )

        ctx = notifications(req)

        self.assertEqual(len(ctx["notifications"]), 2)  # pending follow_request + one follow
        types_and_senders = {(n.notification_type, n.sender_id) for n in ctx["notifications"]}
        self.assertSetEqual(
            types_and_senders,
            {
                ("follow_request", self.pending_sender.id),
                ("follow", self.follower_sender.id),
            },
        )
        self.assertEqual(ctx["unread_notifications_count"], 2)
        self.assertSetEqual(ctx["following_ids"], {self.pending_sender.id, self.follower_sender.id})

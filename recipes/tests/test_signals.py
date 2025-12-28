from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call
from django.test import TestCase

from recipes import signals  


class NotificationSignalsTests(TestCase):
    def setUp(self):
        
        self.notification_patcher = patch("recipes.signals.Notification")
        self.user_patcher = patch("recipes.signals.User")

        self.MockNotification = self.notification_patcher.start()
        self.MockUser = self.user_patcher.start()

        
        self.MockUser.DoesNotExist = type("DoesNotExist", (Exception,), {})

    def tearDown(self):
        self.notification_patcher.stop()
        self.user_patcher.stop()

    def _make_comment(self, author, commenter, text):
        post = SimpleNamespace(author=author)
        return post, SimpleNamespace(user=commenter, recipe_post=post, text=text)

    

    def test_notify_on_like_creates_notification_for_non_author(self):
        self.MockNotification.objects.create.reset_mock()

        author = object()
        liker = object()
        post = SimpleNamespace(author=author)
        like_instance = SimpleNamespace(user=liker, recipe_post=post)

        signals.notify_on_like(
            sender=None,
            instance=like_instance,
            created=True,
        )

        self.MockNotification.objects.create.assert_called_once_with(
            recipient=author,
            sender=liker,
            notification_type="like",
            post=post,
        )

    def test_notify_on_like_does_not_notify_when_liker_is_author(self):
        self.MockNotification.objects.create.reset_mock()

        author = object()
        post = SimpleNamespace(author=author)
        like_instance = SimpleNamespace(user=author, recipe_post=post)

        signals.notify_on_like(
            sender=None,
            instance=like_instance,
            created=True,
        )

        self.MockNotification.objects.create.assert_not_called()

    def test_notify_on_like_does_nothing_when_not_created(self):
        self.MockNotification.objects.create.reset_mock()

        author = object()
        liker = object()
        post = SimpleNamespace(author=author)
        like_instance = SimpleNamespace(user=liker, recipe_post=post)

        signals.notify_on_like(
            sender=None,
            instance=like_instance,
            created=False,
        )

        self.MockNotification.objects.create.assert_not_called()

    

    def test_notify_on_follow_creates_notification_when_created(self):
        self.MockNotification.objects.create.reset_mock()

        author = object()
        follower = object()
        follower_instance = SimpleNamespace(
            author=author,
            follower=follower,
        )

        signals.notify_on_follow(
            sender=None,
            instance=follower_instance,
            created=True,
        )

        self.MockNotification.objects.create.assert_called_once_with(
            recipient=author,
            sender=follower,
            notification_type="follow",
        )

    def test_notify_on_follow_does_nothing_when_not_created(self):
        self.MockNotification.objects.create.reset_mock()

        author = object()
        follower = object()
        follower_instance = SimpleNamespace(
            author=author,
            follower=follower,
        )

        signals.notify_on_follow(
            sender=None,
            instance=follower_instance,
            created=False,
        )

        self.MockNotification.objects.create.assert_not_called()

    

    def test_notify_on_comment_notifies_post_author_for_new_comment_from_other_user(self):
        self.MockNotification.objects.create.reset_mock()

        author, commenter = object(), object()
        post, comment_instance = self._make_comment(author, commenter, "Just a comment.")

        signals.notify_on_comment(sender=None, instance=comment_instance, created=True)

        self.MockNotification.objects.create.assert_called_once_with(
            recipient=author,
            sender=commenter,
            notification_type="comment",
            post=post,
            comment=comment_instance,
        )

    def test_notify_on_comment_skips_comment_notification_when_author_comments_own_post(self):
        self.MockNotification.objects.create.reset_mock()

        author = object()
        post = SimpleNamespace(author=author)
        comment_instance = SimpleNamespace(
            user=author,
            recipe_post=post,
            text="Commenting own post",
        )

        signals.notify_on_comment(
            sender=None,
            instance=comment_instance,
            created=True,
        )

        self.MockNotification.objects.create.assert_not_called()

    def test_notify_on_comment_creates_tag_notifications_for_mentions(self):
        self.MockNotification.objects.create.reset_mock()
        author = object()
        commenter = object()
        tagged_user = object()
        post, comment_instance = self._make_comment(
            author,
            commenter,
            "Hello @alice @missing and @self",
        )
        def lookup(username):
            mapping = {"alice": tagged_user, "self": commenter}
            if username in mapping:
                return mapping[username]
            raise self.MockUser.DoesNotExist()
        self.MockUser.objects.get.side_effect = lookup

        signals.notify_on_comment(sender=None, instance=comment_instance, created=True)

        calls = self.MockNotification.objects.create.call_args_list
        recipients = {(c.kwargs["notification_type"], c.kwargs["recipient"]) for c in calls}
        self.assertEqual(len(calls), 2)
        self.assertSetEqual(recipients, {("comment", author), ("tag", tagged_user)})

    def test_notify_on_comment_does_nothing_when_not_created(self):
        self.MockNotification.objects.create.reset_mock()

        author = object()
        commenter = object()
        post = SimpleNamespace(author=author)
        comment_instance = SimpleNamespace(
            user=commenter,
            recipe_post=post,
            text="Editing existing comment",
        )

        signals.notify_on_comment(
            sender=None,
            instance=comment_instance,
            created=False,
        )

        self.MockNotification.objects.create.assert_not_called()

    

    def test_trim_notification_history_does_nothing_when_not_created(self):
        self.MockNotification.objects.filter.reset_mock()

        instance = SimpleNamespace(recipient="user-x")

        signals.trim_notification_history(
            sender=None,
            instance=instance,
            created=False,
        )

        self.MockNotification.objects.filter.assert_not_called()

    def test_trim_notification_history_keeps_latest_and_deletes_older(self):
        self.MockNotification.objects.filter.reset_mock()

        instance = SimpleNamespace(recipient="user-x")

        mock_qs = MagicMock()
        mock_values_qs = MagicMock()

        self.MockNotification.objects.filter.return_value = mock_qs
        mock_qs.order_by.return_value = mock_values_qs
        mock_values_qs.values_list.return_value = [1, 2, 3]

        signals.trim_notification_history(
            sender=None,
            instance=instance,
            created=True,
        )

        self.MockNotification.objects.filter.assert_any_call(recipient="user-x")
        mock_qs.order_by.assert_called_once_with("-created_at", "-id")
        mock_values_qs.values_list.assert_called_once_with("id", flat=True)

        mock_qs.exclude.assert_called_once_with(id__in=[1, 2, 3])
        mock_qs.exclude.return_value.delete.assert_called_once_with()

    def test_trim_notification_history_no_delete_when_keep_ids_empty(self):
        self.MockNotification.objects.filter.reset_mock()

        instance = SimpleNamespace(recipient="user-x")

        mock_qs = MagicMock()
        mock_values_qs = MagicMock()

        self.MockNotification.objects.filter.return_value = mock_qs
        mock_qs.order_by.return_value = mock_values_qs
        mock_values_qs.values_list.return_value = []

        signals.trim_notification_history(
            sender=None,
            instance=instance,
            created=True,
        )

        self.MockNotification.objects.filter.assert_called_once_with(recipient="user-x")
        mock_qs.order_by.assert_called_once_with("-created_at", "-id")
        mock_values_qs.values_list.assert_called_once_with("id", flat=True)

        mock_qs.exclude.assert_not_called()

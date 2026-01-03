from types import SimpleNamespace
from unittest.mock import MagicMock

from django.test import TestCase

from recipes.services.notifications import NotificationService


class NotificationServiceTests(TestCase):
    def test_filter_notifications_skips_pending_and_duplicates(self):
        svc = NotificationService(notification_model=MagicMock(), follower_model=MagicMock())
        pending_ids = {1}
        notifs = [
            SimpleNamespace(notification_type="follow", sender_id=1),
            SimpleNamespace(notification_type="follow", sender_id=2),
            SimpleNamespace(notification_type="follow", sender_id=2),
            SimpleNamespace(notification_type="comment", sender_id=3),
        ]

        filtered = svc.filter_notifications(notifs, pending_ids)

        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0].notification_type, "follow")
        self.assertEqual(filtered[0].sender_id, 2)
        self.assertEqual(filtered[1].notification_type, "comment")

    def test_mark_all_read_updates_unread_notifications(self):
        mock_qs = MagicMock()
        mock_model = MagicMock()
        mock_model.objects.filter.return_value = mock_qs
        svc = NotificationService(notification_model=mock_model, follower_model=MagicMock())

        svc.mark_all_read(user="user")

        mock_model.objects.filter.assert_called_once_with(recipient="user", is_read=False)
        mock_qs.update.assert_called_once_with(is_read=True)

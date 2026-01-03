from types import SimpleNamespace
from unittest.mock import MagicMock

from django.test import TestCase

from recipes.services.notifications import NotificationService


class NotificationServiceAdditionalTests(TestCase):
    def test_visible_notifications_runs_filter(self):
        notif_model = MagicMock()
        qs = MagicMock()
        qs.exclude.return_value.select_related.return_value.prefetch_related.return_value.order_by.return_value = [
            SimpleNamespace(notification_type="follow", sender_id=1)
        ]
        notif_model.objects.filter.return_value = qs
        svc = NotificationService(notification_model=notif_model, follower_model=MagicMock())

        filtered = svc.visible_notifications(user="user")

        self.assertEqual(len(filtered), 1)

    def test_following_ids_returns_set(self):
        follower_model = MagicMock()
        follower_model.objects.filter.return_value.values_list.return_value = [1, 2]
        svc = NotificationService(notification_model=MagicMock(), follower_model=follower_model)

        ids = svc.following_ids("user")

        follower_model.objects.filter.assert_called_once_with(follower="user")
        self.assertEqual(ids, {1, 2})

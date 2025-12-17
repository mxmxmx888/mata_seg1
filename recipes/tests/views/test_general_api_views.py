from django.test import TestCase
from django.urls import reverse
from recipes.models import User, Notification

class GeneralApiViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='johndoe', 
            email='test@example.com', 
            password='Password123'
        )
        self.other_user = User.objects.create_user(
            username='sender',
            email='sender@example.com',
            password='Password123'
        )
        self.client.login(email='test@example.com', password='Password123')
        self.url = reverse('mark_notifications_read')

    def test_mark_notifications_read(self):
        Notification.objects.create(
            recipient=self.user,
            sender=self.other_user,
            notification_type='like',
            is_read=False
        )
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'status': 'success'})
        self.assertFalse(Notification.objects.filter(is_read=False).exists())
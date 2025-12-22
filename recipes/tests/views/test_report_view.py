from django.test import TestCase
from django.urls import reverse
from recipes.models import User, RecipePost, Comment

class ReportViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='johndoe', 
            email='test@example.com', 
            password='Password123'
        )
        self.post = RecipePost.objects.create(
            author=self.user, 
            title="Pancakes", 
            description="Yum"
        )
        self.comment = Comment.objects.create(
            recipe_post=self.post, 
            user=self.user, 
            text="Bad comment"
        )
        self.client.login(email='test@example.com', password='Password123')

    def test_report_recipe_success(self):
        url = reverse('report_content', kwargs={'content_type': 'recipe', 'object_id': self.post.id})
        data = {'reason': 'spam', 'description': 'This is spam.'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

    def test_report_comment_success(self):
        url = reverse('report_content', kwargs={'content_type': 'comment', 'object_id': self.comment.id})
        data = {'reason': 'harassment', 'description': 'Harassing comment.'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

    def test_report_invalid_content_type(self):
        url = reverse('report_content', kwargs={'content_type': 'invalid', 'object_id': self.post.id})
        data = {'reason': 'spam'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

    def test_get_report_form_renders(self):
        url = reverse('report_content', kwargs={'content_type': 'recipe', 'object_id': self.post.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'content/report_content.html')
        self.assertIn('form', response.context)

    def test_invalid_report_form_renders_errors(self):
        url = reverse('report_content', kwargs={'content_type': 'recipe', 'object_id': self.post.id})
        response = self.client.post(url, data={"description": ""})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'content/report_content.html')

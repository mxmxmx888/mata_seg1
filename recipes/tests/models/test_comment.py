from django.core.exceptions import ValidationError
from django.test import TestCase

from recipes.models.comment import Comment
from recipes.tests.test_utils import make_user, make_recipe_post


class CommentModelTestCase(TestCase):
    def setUp(self):
        self.post_author = make_user(username="@postauthor")
        self.other_user = make_user(username="@commenter")
        self.post = make_recipe_post(author=self.post_author)

    def test_user_can_comment_on_post(self):
        comment = Comment.objects.create(
            user=self.other_user,
            recipe_post=self.post,
            text="Looks delicious!",
        )
        self.assertEqual(comment.user, self.other_user)
        self.assertEqual(comment.recipe_post, self.post)
        self.assertEqual(comment.text, "Looks delicious!")

    def test_comment_is_linked_to_post(self):
        comment = Comment.objects.create(
            user=self.other_user,
            recipe_post=self.post,
            text="Nice recipe",
        )
        self.assertEqual(comment.recipe_post, self.post)

    def test_comment_is_linked_to_author(self):
        # your model uses 'user' not 'author'
        comment = Comment.objects.create(
            user=self.other_user,
            recipe_post=self.post,
            text="Amazing!",
        )
        self.assertEqual(comment.user, self.other_user)

    def test_multiple_comments_allowed(self):
        Comment.objects.create(
            user=self.other_user,
            recipe_post=self.post,
            text="First comment",
        )
        Comment.objects.create(
            user=self.post_author,
            recipe_post=self.post,
            text="Second comment",
        )
        self.assertEqual(Comment.objects.filter(recipe_post=self.post).count(), 2)

    def test_comment_text_cannot_be_empty_if_validated(self):
        """
        This only passes if your model enforces non-empty text via validation.
        If Comment.text is blank=True, delete this test.
        """
        comment = Comment(
            user=self.other_user,
            recipe_post=self.post,
            text="",
        )
        with self.assertRaises(ValidationError):
            comment.full_clean()

    def test_string_representation(self):
        comment = Comment.objects.create(
            user=self.other_user,
            recipe_post=self.post,
            text="So good!",
        )
        # Common patterns: either returns text, or something containing it.
        s = str(comment)
        self.assertTrue(isinstance(s, str))
        self.assertTrue(len(s) > 0)
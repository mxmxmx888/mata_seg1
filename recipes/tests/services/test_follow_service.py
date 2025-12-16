import uuid
from django.utils import timezone
from django.test import TestCase
from recipes.models import User, Follower, FollowRequest, Notification
from recipes.services import FollowService

class FollowServiceTestCase(TestCase):
    fixtures = [
        "recipes/tests/fixtures/default_user.json",
        "recipes/tests/fixtures/other_users.json",
    ]

    def setUp(self):
        self.alice = User.objects.get(username="@johndoe")
        self.bob = User.objects.get(username="@janedoe")
        self.cara = User.objects.get(username="@petrapickles")
        self.cara.is_private = True
        self.cara.save()

    def test_follow_public_user_creates_relation(self):
        service = FollowService(self.alice)
        result = service.follow_user(self.bob)
        self.assertEqual(result["status"], "following")
        self.assertTrue(Follower.objects.filter(follower=self.alice, author=self.bob).exists())
        note = Notification.objects.filter(recipient=self.bob, notification_type="follow").first()
        self.assertIsNotNone(note)

    def test_follow_user_handles_missing_target(self):
        service = FollowService(self.alice)
        res = service.follow_user(None)
        self.assertEqual(res["status"], "noop")

    def test_follow_private_user_creates_request(self):
        service = FollowService(self.alice)
        output = service.follow_user(self.cara)
        self.assertEqual(output["status"], "requested")
        fr = FollowRequest.objects.get(requester=self.alice, target=self.cara)
        self.assertEqual(fr.status, FollowRequest.STATUS_PENDING)
        self.assertTrue(Notification.objects.filter(follow_request=fr).exists())

    def test_follow_user_noop_when_same_user(self):
        service = FollowService(self.alice)
        self.assertEqual(service.follow_user(self.alice)["status"], "noop")

    def test_toggle_follow_cancels_pending_request(self):
        fr = FollowRequest.objects.create(requester=self.alice, target=self.cara)
        service = FollowService(self.alice)
        result = service.toggle_follow(self.cara)
        self.assertEqual(result["status"], "request_cancelled")
        self.assertFalse(FollowRequest.objects.filter(id=fr.id).exists())

    def test_cancel_request_cleans_notifications(self):
        fr = FollowRequest.objects.create(requester=self.alice, target=self.cara)
        Notification.objects.create(recipient=self.cara, sender=self.alice, notification_type="follow_request", follow_request=fr)
        ok = FollowService(self.alice).cancel_request(self.cara)
        self.assertTrue(ok)
        self.assertFalse(FollowRequest.objects.filter(id=fr.id).exists())
        self.assertFalse(Notification.objects.filter(recipient=self.cara).exists())

    def test_accept_request_creates_follower(self):
        fr = FollowRequest.objects.create(requester=self.alice, target=self.bob, status=FollowRequest.STATUS_PENDING, created_at=timezone.now())
        service = FollowService(self.bob)
        success = service.accept_request(fr.id)
        self.assertTrue(success)
        fr.refresh_from_db()
        self.assertEqual(fr.status, FollowRequest.STATUS_ACCEPTED)
        self.assertTrue(Follower.objects.filter(follower=self.alice, author=self.bob).exists())

    def test_reject_request_changes_status(self):
        fr = FollowRequest.objects.create(requester=self.alice, target=self.bob, status=FollowRequest.STATUS_PENDING)
        service = FollowService(self.bob)
        ok = service.reject_request(fr.id)
        self.assertTrue(ok)
        fr.refresh_from_db()
        self.assertEqual(fr.status, FollowRequest.STATUS_REJECTED)

    def test_unfollow_removes_relation(self):
        Follower.objects.create(follower=self.alice, author=self.bob)
        service = FollowService(self.alice)
        self.assertTrue(service.unfollow(self.bob))
        self.assertFalse(Follower.objects.filter(follower=self.alice, author=self.bob).exists())

    def test_follow_user_when_already_following(self):
        Follower.objects.create(follower=self.alice, author=self.bob)
        service = FollowService(self.alice)
        result = service.follow_user(self.bob)
        self.assertEqual(result["status"], "following")

    def test_cancel_request_no_actor_is_noop(self):
        service = FollowService(None)
        self.assertFalse(service.cancel_request(self.bob))

    def test_toggle_follow_unfollows(self):
        Follower.objects.create(follower=self.alice, author=self.bob)
        out = FollowService(self.alice).toggle_follow(self.bob)
        self.assertEqual(out["status"], "unfollowed")
        self.assertFalse(Follower.objects.filter(follower=self.alice, author=self.bob).exists())

    def test_cleanup_follow_back_prompt_on_follow(self):
        Notification.objects.create(recipient=self.alice, sender=self.bob, notification_type="follow")
        FollowService(self.alice).follow_user(self.bob)
        self.assertFalse(Notification.objects.filter(recipient=self.alice, sender=self.bob).exists())

    def test_accept_request_missing_returns_false(self):
        ok = FollowService(self.alice).accept_request(uuid.uuid4())
        self.assertFalse(ok)

    def test_reject_request_missing_returns_false(self):
        ok = FollowService(self.alice).reject_request(uuid.uuid4())
        self.assertFalse(ok)

    def test_follow_user_updates_existing_request(self):
        fr = FollowRequest.objects.create(requester=self.alice, target=self.cara, status=FollowRequest.STATUS_REJECTED)
        result = FollowService(self.alice).follow_user(self.cara)
        fr.refresh_from_db()
        self.assertEqual(result["status"], "requested")
        self.assertEqual(fr.status, FollowRequest.STATUS_PENDING)

    def test_toggle_follow_when_not_authenticated(self):
        guest_service = FollowService(None)
        out = guest_service.toggle_follow(self.bob)
        self.assertEqual(out["status"], "noop")

    def test_cleanup_request_prompt_runs(self):
        fr = FollowRequest.objects.create(requester=self.alice, target=self.cara)
        Notification.objects.create(recipient=self.cara, sender=self.alice, notification_type="follow_request", follow_request=fr)
        FollowService(self.alice).cancel_request(self.cara)
        self.assertFalse(Notification.objects.filter(recipient=self.cara).exists())

    def test_follow_public_removes_pending_request(self):
        fr = FollowRequest.objects.create(requester=self.alice, target=self.bob)
        out = FollowService(self.alice).follow_user(self.bob)
        self.assertEqual(out["status"], "following")
        self.assertFalse(FollowRequest.objects.filter(id=fr.id).exists())

    def test_unfollow_no_actor_noop(self):
        response = FollowService(None).unfollow(self.bob)
        self.assertFalse(response)

    def test_follow_private_existing_pending_keeps_status(self):
        fr = FollowRequest.objects.create(requester=self.alice, target=self.cara, status=FollowRequest.STATUS_PENDING)
        res = FollowService(self.alice).follow_user(self.cara)
        fr.refresh_from_db()
        self.assertEqual(res["status"], "requested")
        self.assertEqual(fr.status, FollowRequest.STATUS_PENDING)

    def test_follow_private_resets_rejected_request(self):
        fr = FollowRequest.objects.create(requester=self.alice, target=self.cara, status=FollowRequest.STATUS_REJECTED, created_at=timezone.now())
        before = fr.created_at
        try:
            result = FollowService(self.alice).follow_user(self.cara)
        except Exception as exc:
            self.fail(f"unexpected error {exc}")
        fr.refresh_from_db()
        self.assertEqual(result["status"], "requested")
        self.assertNotEqual(fr.created_at, before)

    def test_toggle_follow_calls_follow_user_branch(self):
        try:
            res = FollowService(self.alice).toggle_follow(self.bob)
        except Exception as exc:
            self.fail(str(exc))
        self.assertIn(res["status"], {"following", "requested"})

    def test_unfollow_same_user_is_noop(self):
        service = FollowService(self.alice)
        self.assertFalse(service.unfollow(self.alice))

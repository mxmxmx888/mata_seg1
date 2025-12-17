from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.views import View
from recipes.views.decorators import login_prohibited, LoginProhibitedMixin

class LoginProhibitedMixinTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_login_prohibited_throws_exception_when_not_configured(self):
        mixin = LoginProhibitedMixin()
        with self.assertRaises(ImproperlyConfigured):
            mixin.get_redirect_when_logged_in_url()

    def test_login_prohibited_redirects_authenticated_user(self):
        @login_prohibited
        def dummy(request):
            return HttpResponse("ok")
        request = self.factory.get("/")
        request.user = type("U", (), {"is_authenticated": True})()
        response = dummy(request)
        self.assertIn(settings.REDIRECT_URL_WHEN_LOGGED_IN.strip("/"), response.url)

    def test_login_prohibited_allows_anonymous(self):
        @login_prohibited
        def dummy(request):
            return HttpResponse("anon")
        request = self.factory.get("/")
        request.user = AnonymousUser()
        response = dummy(request)
        self.assertEqual(response.content.decode(), "anon")

    def test_login_prohibited_mixin_redirects_on_dispatch(self):
        class DummyView(LoginProhibitedMixin, View):
            redirect_when_logged_in_url = "/somewhere/"
            def get(self, request):
                return HttpResponse("hey")
        request = self.factory.get("/")
        request.user = type("U", (), {"is_authenticated": True})()
        view = DummyView.as_view()
        response = view(request)
        self.assertEqual(response.url, "/somewhere/")

    def test_login_prohibited_mixin_allows_guest(self):
        class DummyView(LoginProhibitedMixin, View):
            redirect_when_logged_in_url = "/to/"
            def get(self, request):
                return HttpResponse("fine")
        request = self.factory.get("/")
        request.user = AnonymousUser()
        resp = DummyView.as_view()(request)
        self.assertEqual(resp.content.decode(), "fine")

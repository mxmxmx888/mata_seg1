from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView
from recipes.forms import PasswordResetRequestForm, UsernameResetRequestForm
from recipes.views.decorators import LoginProhibitedMixin
from recipes.firebase_auth_services import generate_password_reset_link
from recipes.services.users import UserService

user_service = UserService()


class PasswordResetRequestView(LoginProhibitedMixin, FormView):
    """Handle password reset link requests for unauthenticated users."""
    template_name = 'auth/password_reset_request.html'
    form_class = PasswordResetRequestForm
    success_url = reverse_lazy('password_reset_done')
    redirect_when_logged_in_url = settings.REDIRECT_URL_WHEN_LOGGED_IN

    # ✅ makes it patchable in tests without touching Firebase
    reset_link_generator = staticmethod(generate_password_reset_link)

    def form_valid(self, form):
        """Send reset email if user exists, then redirect with neutral response."""
        email = form.cleaned_data['email']
        user = user_service.first_by_email(email)

        if user:
            link = self.reset_link_generator(email)

            if link:
                send_mail(
                    subject='Password Reset Request',
                    message=f'Click the following link to reset your password: {link}',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )

        # Always respond the same (no user-enumeration)
        return super().form_valid(form)


class PasswordResetDoneView(LoginProhibitedMixin, TemplateView):
    """Display confirmation after password reset email is sent."""
    template_name = 'auth/password_reset_done.html'
    redirect_when_logged_in_url = settings.REDIRECT_URL_WHEN_LOGGED_IN


class UsernameResetRequestView(LoginProhibitedMixin, FormView):
    """Handle username recovery requests for unauthenticated users."""
    template_name = 'auth/username_reset_request.html'
    form_class = UsernameResetRequestForm
    success_url = reverse_lazy('username_reset_done')
    redirect_when_logged_in_url = settings.REDIRECT_URL_WHEN_LOGGED_IN

    def form_valid(self, form):
        """Send username reminder if user exists, then redirect."""
        email = form.cleaned_data['email']
        user = user_service.first_by_email(email)

        if user:
            send_mail(
                subject='Username Recovery',
                message=f'Hello! The username associated with this email is: {user.username}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )

        return super().form_valid(form)


class UsernameResetDoneView(LoginProhibitedMixin, TemplateView):
    """Display confirmation after username recovery email is sent."""
    template_name = 'auth/username_reset_done.html'
    redirect_when_logged_in_url = settings.REDIRECT_URL_WHEN_LOGGED_IN

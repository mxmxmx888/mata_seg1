from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView
from recipes.forms import PasswordResetRequestForm, UsernameResetRequestForm
from recipes.models import User
from recipes.views.decorators import LoginProhibitedMixin
from recipes.firebase_auth_services import generate_password_reset_link


class PasswordResetRequestView(LoginProhibitedMixin, FormView):
    """
    Collect the user's email address to start a password reset flow.

    The form intentionally behaves the same regardless of whether an account
    exists to avoid leaking user existence.
    """

    template_name = 'password_reset_request.html'
    form_class = PasswordResetRequestForm
    success_url = reverse_lazy('password_reset_done')
    redirect_when_logged_in_url = settings.REDIRECT_URL_WHEN_LOGGED_IN

    def form_valid(self, form):
        """
        Accept the email and proceed to the confirmation step.
        """
        email = form.cleaned_data['email']
        
        user = User.objects.filter(email=email).first()
        
        if user:
            link = generate_password_reset_link(email)
            
            if link:
                send_mail(
                    subject='Password Reset Request',
                    message=f'Click the following link to reset your password: {link}',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
            else:
                print(f"Failed to generate Firebase reset link for {email}")

        return super().form_valid(form)


class PasswordResetDoneView(LoginProhibitedMixin, TemplateView):
    """Show a neutral confirmation after a reset request is submitted."""

    template_name = 'password_reset_done.html'
    redirect_when_logged_in_url = settings.REDIRECT_URL_WHEN_LOGGED_IN


class UsernameResetRequestView(LoginProhibitedMixin, FormView):
    """
    Collect the user's email address to help recover their username.

    The flow mirrors the password reset experience and keeps responses neutral
    to avoid leaking account existence.
    """

    template_name = 'username_reset_request.html'
    form_class = UsernameResetRequestForm
    success_url = reverse_lazy('username_reset_done')
    redirect_when_logged_in_url = settings.REDIRECT_URL_WHEN_LOGGED_IN

    def form_valid(self, form):
        """
        Accept the email and proceed to the confirmation step.
        """
        email = form.cleaned_data['email']
        
        user = User.objects.filter(email=email).first()
        
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
    """Show a neutral confirmation after a username reset request."""

    template_name = 'username_reset_done.html'
    redirect_when_logged_in_url = settings.REDIRECT_URL_WHEN_LOGGED_IN
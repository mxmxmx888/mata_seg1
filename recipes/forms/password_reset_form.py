from django import forms


class PasswordResetRequestForm(forms.Form):
    """
    Collect an email address to start a password reset flow.

    The form deliberately does not validate whether the email is attached to
    a user account so we can always show the same confirmation message.
    """

    email = forms.EmailField(label="Email address")

import logging

from django.conf import settings
from django.views.csrf import csrf_failure as default_csrf_failure

logger = logging.getLogger(__name__)


def csrf_debug_failure(request, reason="", template_name="403_csrf.html"):
    """
    Mirror Django's default CSRF failure view but add rich logging for debugging.

    This runs only in DEBUG because settings.CSRF_FAILURE_VIEW is set conditionally.
    """
    cookie_token = request.COOKIES.get(settings.CSRF_COOKIE_NAME)
    post_token = request.POST.get("csrfmiddlewaretoken")
    header_token = request.META.get("HTTP_X_CSRFTOKEN")
    logger.warning(
        "CSRF failure: reason=%s host=%s path=%s referer=%s cookie=%s post=%s header=%s user=%s",
        reason,
        request.get_host(),
        request.path,
        request.META.get("HTTP_REFERER"),
        cookie_token,
        post_token,
        header_token,
        getattr(request, "user", None),
    )
    return default_csrf_failure(request, reason=reason, template_name=template_name)

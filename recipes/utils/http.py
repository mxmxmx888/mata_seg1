"""HTTP-related utility helpers."""


def is_ajax(request):
    """Detect HTMX/XMLHttpRequest headers or an explicit ajax query flag."""
    hx_header = request.headers.get("HX-Request")
    xhr_header = request.headers.get("x-requested-with")
    return bool(
        hx_header
        or xhr_header == "XMLHttpRequest"
        or request.GET.get("ajax") == "1"
    )

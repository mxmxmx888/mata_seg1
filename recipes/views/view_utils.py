def is_ajax_request(request):
    """
    Return True when the request was triggered via HTMX or XMLHttpRequest headers.
    """
    header = request.headers.get("HX-Request") or request.headers.get("x-requested-with")
    return bool(header == "XMLHttpRequest" or header)

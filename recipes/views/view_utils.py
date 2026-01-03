from recipes.utils.http import is_ajax


def is_ajax_request(request):
    """
    Return True when the request was triggered via HTMX/XMLHttpRequest headers
    or an explicit ajax query flag.
    """
    return is_ajax(request)

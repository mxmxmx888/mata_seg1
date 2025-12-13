from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from recipes.services import FollowService

@login_required
def accept_follow_request(request, request_id):
    if request.method != "POST":
        return HttpResponseForbidden()
    service = FollowService(request.user)
    ok = service.accept_request(request_id)
    redirect_to = request.META.get("HTTP_REFERER") or reverse("dashboard")
    return HttpResponseRedirect(redirect_to) if ok else HttpResponseRedirect(redirect_to)

@login_required
def reject_follow_request(request, request_id):
    if request.method != "POST":
        return HttpResponseForbidden()
    service = FollowService(request.user)
    ok = service.reject_request(request_id)
    redirect_to = request.META.get("HTTP_REFERER") or reverse("dashboard")
    return HttpResponseRedirect(redirect_to) if ok else HttpResponseRedirect(redirect_to)

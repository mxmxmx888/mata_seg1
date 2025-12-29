"""Shared logic for profile view rendering, pagination, and form handling."""

from dataclasses import dataclass

from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string

FOLLOW_LIST_PAGE_SIZE = 25


@dataclass(frozen=True)
class ProfileDeps:
    messages: object
    user_form_cls: object
    password_form_cls: object
    follow_service_factory: object
    privacy_service: object
    post_repo: object
    user_repo: object
    profile_data_for_user: object
    collections_for_user: object
    follower_model: object
    close_friend_model: object
    follow_request_model: object
    favourite_model: object
    favourite_item_model: object
    recipe_post_model: object


def paginate_follow_queryset(qs, user_attr, page_size=FOLLOW_LIST_PAGE_SIZE, page_number=1):
    """Return total, sliced users, and pagination flags for a follow queryset."""
    total = qs.count()
    start = (max(1, page_number) - 1) * page_size
    end = start + page_size
    users = [getattr(relation, user_attr) for relation in qs[start:end]]
    has_more = total > end
    next_page = page_number + 1 if has_more else None
    return total, users, has_more, next_page


def follow_page_data(qs, user_attr):
    total, users, has_more, next_page = paginate_follow_queryset(qs, user_attr)
    return {"count": total, "users": users, "has_more": has_more, "next_page": next_page, "visible": True}


def can_view_follow_lists(profile_user, viewer, is_following):
    return profile_user == viewer or not getattr(profile_user, "is_private", False) or is_following


def apply_follow_visibility(profile_user, viewer, is_following, followers, following):
    if can_view_follow_lists(profile_user, viewer, is_following):
        return followers, following
    hidden = {"users": [], "has_more": False, "next_page": None, "visible": False}
    return {**followers, **hidden}, {**following, **hidden}


def follow_summary(followers, following, close_friend_ids, close_friends, is_following, pending_request):
    visible = following["visible"]
    return {
        "followers_count": followers["count"],
        "following_count": following["count"],
        "followers_users": followers["users"],
        "following_users": following["users"],
        "close_friend_ids": close_friend_ids,
        "close_friends": close_friends,
        "followers_has_more": followers["has_more"],
        "followers_next_page": followers["next_page"],
        "following_has_more": following["has_more"],
        "following_next_page": following["next_page"],
        "is_following": is_following,
        "pending_request": pending_request,
        "can_view_follow_lists": visible,
        "close_friends_has_more": followers["has_more"] if visible else False,
        "close_friends_next_page": followers["next_page"] if visible else None,
    }


def is_following_profile(viewer, profile_user, deps):
    if profile_user == viewer:
        return False
    return deps.follower_model.objects.filter(follower=viewer, author=profile_user).exists()


def pending_follow_request(viewer, profile_user, is_following, deps):
    if profile_user == viewer or is_following or not getattr(profile_user, "is_private", False):
        return None
    return deps.follow_request_model.objects.filter(
        requester=viewer,
        target=profile_user,
        status=deps.follow_request_model.STATUS_PENDING,
    ).first()


def follow_context(profile_user, viewer, deps):
    followers = follow_page_data(
        deps.follower_model.objects.filter(author=profile_user).select_related("follower"),
        "follower",
    )
    following = follow_page_data(
        deps.follower_model.objects.filter(follower=profile_user).select_related("author"),
        "author",
    )
    close_friend_ids = set(
        deps.close_friend_model.objects.filter(owner=profile_user).values_list("friend_id", flat=True)
    )
    close_friends = [u for u in followers["users"] if u.id in close_friend_ids]
    is_following = is_following_profile(viewer, profile_user, deps)
    pending_request = pending_follow_request(viewer, profile_user, is_following, deps)
    followers, following = apply_follow_visibility(profile_user, viewer, is_following, followers, following)
    return follow_summary(followers, following, close_friend_ids, close_friends, is_following, pending_request)


def profile_user_from_request(request, deps):
    username = request.GET.get("user")
    if not username:
        return request.user
    try:
        return deps.user_repo.get_by_username(username)
    except deps.user_repo.model.DoesNotExist:
        raise Http404("User not found")


def follow_list_selection(list_type, profile_user, is_own_profile, deps):
    if list_type == "followers":
        qs = deps.follower_model.objects.filter(author=profile_user).select_related("follower")
        return qs, "follower", "partials/profile/follow_list_items.html"
    if list_type == "following":
        qs = deps.follower_model.objects.filter(follower=profile_user).select_related("author")
        return qs, "author", "partials/profile/follow_list_items.html"
    if list_type == "close_friends":
        if not is_own_profile:
            return JsonResponse({"error": "Not allowed"}, status=403)
        qs = deps.follower_model.objects.filter(author=profile_user).select_related("follower")
        return qs, "follower", "partials/profile/close_friend_items.html"
    return JsonResponse({"error": "Unknown list"}, status=400)


def profile_stats(profile_user, follow_ctx, deps):
    data = deps.profile_data_for_user(profile_user)
    data["followers"] = follow_ctx["followers_count"]
    data["following"] = follow_ctx["following_count"]
    data["close_friends_count"] = len(follow_ctx["close_friend_ids"])
    return data


def profile_setup(request, deps):
    profile_user = profile_user_from_request(request, deps)
    follow_ctx = follow_context(profile_user, request.user, deps)
    return profile_user, profile_user == request.user, follow_ctx, profile_stats(profile_user, follow_ctx, deps)


def profile_posts(profile_user, viewer, deps):
    can_view_profile = deps.privacy_service.can_view_profile(viewer, profile_user)
    if not can_view_profile:
        return deps.recipe_post_model.objects.none(), can_view_profile
    posts_qs = deps.post_repo.list_for_user(profile_user.id, order_by=("-created_at",))
    if profile_user != viewer:
        posts_qs = deps.privacy_service.filter_visible_posts(posts_qs, viewer)
    return posts_qs, can_view_profile


def profile_posts_page(profile_user, viewer, page_number, deps, page_size=12):
    posts_qs, can_view_profile = profile_posts(profile_user, viewer, deps)
    start = (page_number - 1) * page_size
    end = start + page_size
    posts_page = list(posts_qs[start:end]) if can_view_profile else []
    posts_has_more = posts_qs.count() > end if can_view_profile else False
    return posts_page, posts_has_more, can_view_profile


def posts_for_profile(request, profile_user, deps):
    page_number = max(1, int(request.GET.get("page") or 1))
    posts_page, posts_has_more, can_view_profile = profile_posts_page(profile_user, request.user, page_number, deps)
    return posts_page, posts_has_more, can_view_profile, page_number


def is_posts_only(request):
    return request.headers.get("HX-Request") and request.GET.get("posts_only") == "1"


def profile_posts_context(request, profile_user, deps):
    posts_page, posts_has_more, can_view_profile, page_number = posts_for_profile(request, profile_user, deps)
    hx_response = None
    if is_posts_only(request):
        hx_response = render(request, "partials/feed/feed_cards.html", {"posts": posts_page, "request": request})
    return {
        "hx": bool(hx_response),
        "response": hx_response,
        "posts_page": posts_page,
        "posts_has_more": posts_has_more,
        "page_number": page_number,
        "can_view_profile": can_view_profile,
    }


def save_profile_form(form, deps):
    changed_fields = set(form.changed_data)
    if not changed_fields:
        return
    form.save()
    non_avatar_changes = changed_fields - {"avatar", "remove_avatar"}
    if non_avatar_changes:
        deps.messages.add_message(form.request, deps.messages.SUCCESS, "Profile updated!")


def handle_profile_post(request, profile_user, deps):
    if request.POST.get("cancel_request") == "1":
        service = deps.follow_service_factory(request.user)
        service.cancel_request(profile_user)
        return redirect(request.get_full_path()), None, None, None
    if profile_user != request.user:
        return redirect("profile"), None, None, None
    form = deps.user_form_cls(request.POST, request.FILES, instance=request.user)
    edit_profile_form = form
    show_modal = True
    if form.is_valid():
        form.request = request
        save_profile_form(form, deps)
        request.session["show_edit_profile_modal"] = True
        return redirect("profile"), form, edit_profile_form, show_modal
    return None, form, edit_profile_form, show_modal


def profile_forms(request, profile_user, is_own_profile, deps):
    edit_profile_form = deps.user_form_cls(instance=request.user)
    password_form = deps.password_form_cls(user=request.user)
    show_edit_profile_modal = request.session.pop("show_edit_profile_modal", False)
    if request.method != "POST":
        form = deps.user_form_cls(instance=request.user) if is_own_profile else None
        return None, form, edit_profile_form, password_form, show_edit_profile_modal
    redirect_response, form, edit_profile_form, show_edit_profile_modal = handle_profile_post(request, profile_user, deps)
    return redirect_response, form, edit_profile_form, password_form, show_edit_profile_modal


def follow_view_block(follow_ctx):
    return {
        "is_following": follow_ctx["is_following"],
        "followers_count": follow_ctx["followers_count"],
        "following_count": follow_ctx["following_count"],
        "followers_users": follow_ctx["followers_users"],
        "following_users": follow_ctx["following_users"],
        "close_friends": follow_ctx["close_friends"],
        "can_view_follow_lists": follow_ctx["can_view_follow_lists"],
        "followers_has_more": follow_ctx["followers_has_more"],
        "followers_next_page": follow_ctx["followers_next_page"],
        "following_has_more": follow_ctx["following_has_more"],
        "following_next_page": follow_ctx["following_next_page"],
        "close_friends_has_more": follow_ctx["close_friends_has_more"],
        "close_friends_next_page": follow_ctx["close_friends_next_page"],
        "pending_follow_request": follow_ctx["pending_request"],
        "close_friend_ids": follow_ctx["close_friend_ids"],
    }


def profile_context(profile_user, viewer, is_own_profile, follow_ctx, profile_data, form, edit_profile_form, password_form, posts, collections, can_view_profile, show_edit_profile_modal):
    return {
        **follow_view_block(follow_ctx),
        "profile": profile_data,
        "collections": collections,
        "form": form,
        "edit_profile_form": edit_profile_form,
        "password_form": password_form,
        "profile_user": profile_user,
        "is_own_profile": is_own_profile,
        "posts": posts,
        "can_view_profile": can_view_profile,
        "show_edit_profile_modal": show_edit_profile_modal,
    }


def profile_render_data(profile_user, is_own_profile, follow_ctx, profile_data, form, edit_profile_form, password_form, posts_page, posts_has_more, page_number, can_view_profile, show_edit_profile_modal):
    return {
        "profile_user": profile_user,
        "is_own_profile": is_own_profile,
        "follow_ctx": follow_ctx,
        "profile_data": profile_data,
        "form": form,
        "edit_profile_form": edit_profile_form,
        "password_form": password_form,
        "posts_page": posts_page,
        "posts_has_more": posts_has_more,
        "page_number": page_number,
        "can_view_profile": can_view_profile,
        "show_edit_profile_modal": show_edit_profile_modal,
    }


def profile_render_data_from_ctx(profile_user, is_own_profile, follow_ctx, profile_data, form, edit_profile_form, password_form, posts_ctx, show_edit_profile_modal):
    return profile_render_data(
        profile_user,
        is_own_profile,
        follow_ctx,
        profile_data,
        form,
        edit_profile_form,
        password_form,
        posts_ctx["posts_page"],
        posts_ctx["posts_has_more"],
        posts_ctx["page_number"],
        posts_ctx["can_view_profile"],
        show_edit_profile_modal,
    )


def full_profile_context(request, data, deps):
    return {
        **profile_context(
            data["profile_user"],
            request.user,
            data["is_own_profile"],
            data["follow_ctx"],
            data["profile_data"],
            data["form"],
            data["edit_profile_form"],
            data["password_form"],
            data["posts_page"],
            deps.collections_for_user(data["profile_user"]),
            data["can_view_profile"],
            data["show_edit_profile_modal"],
        ),
        "posts_has_more": data["posts_has_more"],
        "posts_next_page": data["page_number"] + 1 if data["posts_has_more"] else None,
    }


def render_full_profile(request, data, deps):
    return render(request, "profile/profile.html", full_profile_context(request, data, deps))


def profile_follow_list_response(request, deps):
    profile_user = profile_user_from_request(request, deps)
    is_own_profile = profile_user == request.user
    list_type = request.GET.get("list")
    page_number = max(1, int(request.GET.get("page") or 1))
    follow_ctx = follow_context(profile_user, request.user, deps)
    if not follow_ctx["can_view_follow_lists"]:
        return JsonResponse({"error": "Not allowed"}, status=403)
    selection = follow_list_selection(list_type, profile_user, is_own_profile, deps)
    if isinstance(selection, JsonResponse):
        return selection
    qs, user_attr, template = selection
    total, users, has_more, next_page = paginate_follow_queryset(qs, user_attr, page_number=page_number)
    html = render_to_string(
        template,
        {"users": users, "list_type": list_type, "is_own_profile": is_own_profile, "close_friend_ids": follow_ctx["close_friend_ids"]},
        request=request,
    )
    return JsonResponse({"html": html, "has_more": has_more, "next_page": next_page, "total": total})


def profile_response(request, deps):
    profile_user, is_own_profile, follow_ctx, profile_data = profile_setup(request, deps)
    redirect_response, form, edit_profile_form, password_form, show_edit_profile_modal = profile_forms(
        request, profile_user, is_own_profile, deps
    )
    if redirect_response:
        return redirect_response
    posts_ctx = profile_posts_context(request, profile_user, deps)
    if posts_ctx["hx"]:
        return posts_ctx["response"]
    return render_full_profile(
        request,
        profile_render_data_from_ctx(
            profile_user,
            is_own_profile,
            follow_ctx,
            profile_data,
            form,
            edit_profile_form,
            password_form,
            posts_ctx,
            show_edit_profile_modal,
        ),
        deps,
    )

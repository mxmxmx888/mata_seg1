"""Thin wrappers exposing the feed/search service to dashboard callers."""

from recipes.services.feed import FeedService

feed_service = FeedService()
privacy_service = feed_service.privacy_service

# Public helpers
normalise_tags = feed_service.normalise_tags
user_preference_tags = feed_service.user_preference_tags
preferred_tags_for_user = feed_service.preferred_tags_for_user
base_posts_queryset = feed_service.base_posts_queryset
apply_query_filters = feed_service.apply_query_filters
tag_filtered_qs = feed_service.tag_filtered_qs
score_post_for_user = feed_service.score_post_for_user
score_and_sort_posts = feed_service.score_and_sort_posts
for_you_posts = feed_service.for_you_posts
following_posts = feed_service.following_posts
search_users = feed_service.search_users
filter_posts_by_prep_time = feed_service.filter_posts_by_prep_time

# Backwards-compatible aliases for legacy imports/tests
_normalise_tags = normalise_tags
_user_preference_tags = user_preference_tags
_preferred_tags_for_user = preferred_tags_for_user
_base_posts_queryset = base_posts_queryset
_apply_query_filters = apply_query_filters
_tag_filtered_qs = tag_filtered_qs
_score_post_for_user = score_post_for_user
_score_and_sort_posts = score_and_sort_posts
_get_for_you_posts = for_you_posts
_get_following_posts = following_posts
_search_users = search_users
_filter_posts_by_prep_time = filter_posts_by_prep_time

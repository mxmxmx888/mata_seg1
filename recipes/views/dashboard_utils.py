"""Thin wrappers exposing the feed/search service to dashboard callers."""

from recipes.services.feed import FeedService

feed_service = FeedService()
privacy_service = feed_service.privacy_service

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

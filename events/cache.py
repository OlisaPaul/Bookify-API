"""Cache utilities for the events app."""
from django.core.cache import cache


EVENT_LIST_CACHE_KEY = "events:list"
EVENT_LIST_CACHE_TIMEOUT = 60


def invalidate_event_list_cache():
    """Clear the cached event list response."""
    cache.delete(EVENT_LIST_CACHE_KEY)

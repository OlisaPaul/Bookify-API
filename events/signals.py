"""Signals for cache invalidation in the events app."""
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from events.cache import invalidate_event_list_cache
from events.models import Event


@receiver(post_save, sender=Event)
def clear_event_list_cache_on_save(sender, **kwargs):
    """Invalidate the event list cache after event writes."""
    invalidate_event_list_cache()


@receiver(post_delete, sender=Event)
def clear_event_list_cache_on_delete(sender, **kwargs):
    """Invalidate the event list cache after event deletion."""
    invalidate_event_list_cache()

"""Admin configuration for event models."""
from django.contrib import admin

from events.models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """Basic admin for events."""

    list_display = ("title", "date", "available_slots")
    search_fields = ("title",)

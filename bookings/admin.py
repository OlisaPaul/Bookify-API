"""Admin configuration for booking models."""
from django.contrib import admin

from bookings.models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """Basic admin for bookings."""

    list_display = ("user", "event", "status", "created_at")
    list_filter = ("status",)

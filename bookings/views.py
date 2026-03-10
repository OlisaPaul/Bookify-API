"""Viewsets for booking APIs."""
from django.db import IntegrityError, transaction
from rest_framework import mixins, permissions, serializers, viewsets
from rest_framework.throttling import ScopedRateThrottle

from bookings.models import Booking
from bookings.serializers import BookingSerializer
from events.models import Event


class BookingViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Endpoints for creating and listing the authenticated user's bookings."""

    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "booking_create"

    def get_queryset(self):
        """Restrict booking visibility to the current user."""
        return Booking.objects.filter(user=self.request.user).select_related("event", "user")

    def get_throttles(self):
        """Apply throttling only to booking creation requests."""
        if self.action == "create":
            return [ScopedRateThrottle()]
        return []

    def perform_create(self, serializer):
        """Create bookings inside a transaction to avoid slot races."""
        with transaction.atomic():
            # Lock the event row so concurrent bookings are serialized.
            event = Event.objects.select_for_update().get(
                pk=serializer.validated_data["event"].pk
            )

            if event.available_slots < 1:
                raise serializers.ValidationError(
                    {"event": "No slots available for this event."}
                )

            event.available_slots -= 1
            event.save(update_fields=["available_slots"])

            try:
                serializer.save(user=self.request.user, event=event)
            except IntegrityError as exc:
                raise serializers.ValidationError(
                    {"event": "You have already booked this event."}
                ) from exc

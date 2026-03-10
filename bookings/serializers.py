"""Serializers for booking APIs."""
from rest_framework import serializers

from bookings.models import Booking


class BookingSerializer(serializers.ModelSerializer):
    """Serializer for booking records."""

    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Booking
        fields = ("id", "user", "event", "status", "created_at")
        read_only_fields = ("id", "user", "created_at")

    def validate(self, attrs):
        """Ensure a user cannot create duplicate bookings for the same event."""
        request = self.context.get("request")
        event = attrs.get("event")

        if request is None or request.user.is_anonymous:
            return attrs

        if self.instance is None and Booking.objects.filter(user=request.user, event=event).exists():
            raise serializers.ValidationError(
                {"event": "You have already booked this event."}
            )

        return attrs

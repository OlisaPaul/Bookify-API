"""Viewsets for booking APIs."""
from rest_framework import mixins, permissions, viewsets

from bookings.models import Booking
from bookings.serializers import BookingSerializer


class BookingViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Endpoints for creating and listing the authenticated user's bookings."""

    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Restrict booking visibility to the current user."""
        return Booking.objects.filter(user=self.request.user).select_related("event", "user")

    def perform_create(self, serializer):
        """Attach the authenticated user to new bookings."""
        serializer.save(user=self.request.user)

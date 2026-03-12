"""Viewsets for booking APIs."""
import logging

from django.db import IntegrityError, transaction
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import mixins, permissions, serializers, viewsets
from rest_framework.throttling import ScopedRateThrottle

from bookings.models import Booking
from bookings.serializers import BookingSerializer
from bookings.tasks import process_payment
from core.permissions import IsCustomer, IsStaffOrAdmin
from events.models import Event


logger = logging.getLogger(__name__)


@extend_schema_view(
    create=extend_schema(
        summary="Create a booking",
        description=(
            "Create a booking for the authenticated user. "
            "JWT authentication is required. "
            "Allowed booking status values are `pending`, `paid`, `confirmed`, and `failed`. "
            "Clients should typically submit `pending` on creation; the asynchronous workflow updates the booking status afterward."
        ),
        responses={
            201: BookingSerializer,
            400: OpenApiResponse(description="Validation error, duplicate booking, or no available slots."),
            401: OpenApiResponse(description="Authentication credentials were not provided or are invalid."),
            429: OpenApiResponse(description="Too many booking attempts. Limit is 5 requests per minute."),
        },
        examples=[
            OpenApiExample(
                "Create booking request",
                value={"event": 1, "status": "pending"},
                request_only=True,
            ),
        ],
    )
)
class BookingViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Endpoints for creating and listing the authenticated user's bookings."""

    serializer_class = BookingSerializer
    throttle_scope = "booking_create"

    def get_queryset(self):
        """Restrict booking visibility to the current user."""
        queryset = Booking.objects.select_related("event", "user")
        if self.request.user.is_superuser or self.request.user.role in (
            self.request.user.ROLE_STAFF,
            self.request.user.ROLE_ADMIN,
        ):
            return queryset
        return queryset.filter(user=self.request.user)

    def get_permissions(self):
        """Apply role-based permissions per booking action."""
        if self.action == "create":
            return [permissions.IsAuthenticated(), IsCustomer()]
        return [permissions.IsAuthenticated()]

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
                booking = serializer.save(user=self.request.user, event=event)
            except IntegrityError as exc:
                raise serializers.ValidationError(
                    {"event": "You have already booked this event."}
                ) from exc

            transaction.on_commit(
                lambda: self._enqueue_payment_processing(booking.id)
            )

    def _enqueue_payment_processing(self, booking_id):
        """Queue asynchronous payment processing after a successful commit."""
        try:
            process_payment.delay(booking_id)
        except Exception:
            logger.exception(
                "Failed to enqueue payment processing for booking %s.",
                booking_id,
            )

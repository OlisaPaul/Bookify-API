"""Celery tasks for bookings."""
import logging

from celery import shared_task

from bookings.models import Booking


logger = logging.getLogger(__name__)


@shared_task
def send_booking_confirmation(booking_id):
    """Simulate sending a booking confirmation and mark the booking confirmed."""
    try:
        booking = Booking.objects.select_related("user", "event").get(pk=booking_id)
    except Booking.DoesNotExist:
        logger.warning("Booking confirmation skipped; booking %s does not exist.", booking_id)
        return

    logger.info(
        "Sending booking confirmation for booking %s to user %s for event %s.",
        booking.id,
        booking.user_id,
        booking.event_id,
    )
    booking.status = Booking.STATUS_CONFIRMED
    booking.save(update_fields=["status"])

"""Celery tasks for bookings."""
import logging

from celery import shared_task

from bookings.models import Booking


logger = logging.getLogger(__name__)


def payment_succeeds():
    """Return whether the simulated payment succeeds."""
    return True


@shared_task
def process_payment(booking_id):
    """Simulate payment processing and queue confirmation on success."""
    try:
        booking = Booking.objects.get(pk=booking_id)
    except Booking.DoesNotExist:
        logger.warning("Payment processing skipped; booking %s does not exist.", booking_id)
        return

    payment_succeeded = payment_succeeds()

    if payment_succeeded:
        booking.status = Booking.STATUS_PAID
        booking.save(update_fields=["status"])
        logger.info("Payment processed successfully for booking %s.", booking.id)
        send_booking_confirmation.delay(booking.id)
        return

    booking.status = Booking.STATUS_FAILED
    booking.save(update_fields=["status"])
    logger.warning("Payment failed for booking %s.", booking.id)


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

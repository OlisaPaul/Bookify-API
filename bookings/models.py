"""Models for the bookings app."""
from django.conf import settings
from django.db import models


class Booking(models.Model):
    """Booking created by a user for a specific event."""

    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_CONFIRMED = "confirmed"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_FAILED, "Failed"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    event = models.ForeignKey(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "event"],
                name="unique_booking_per_user_event",
            ),
        ]

    def __str__(self):
        """Return a readable representation for admin and logs."""
        return f"{self.user} - {self.event}"

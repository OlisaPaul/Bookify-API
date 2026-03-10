"""Models for the events app."""
from django.db import models


class Event(models.Model):
    """Event that users can book."""

    title = models.CharField(max_length=255)
    description = models.TextField()
    date = models.DateTimeField()
    available_slots = models.PositiveIntegerField()

    class Meta:
        ordering = ["date", "id"]

    def __str__(self):
        """Return a readable representation for admin and logs."""
        return self.title

"""Viewsets for event APIs."""
from rest_framework import viewsets

from events.models import Event
from events.serializers import EventSerializer


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only endpoints for listing and retrieving events."""

    queryset = Event.objects.all()
    serializer_class = EventSerializer

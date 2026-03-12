"""Viewsets for event APIs."""
from django.core.cache import cache
from rest_framework import permissions, response, viewsets

from core.permissions import IsStaffOrAdmin
from events.cache import EVENT_LIST_CACHE_KEY, EVENT_LIST_CACHE_TIMEOUT
from events.models import Event
from events.serializers import EventSerializer


class EventViewSet(viewsets.ModelViewSet):
    """Endpoints for public event reads and admin event management."""

    queryset = Event.objects.all()
    serializer_class = EventSerializer

    def get_permissions(self):
        """Allow public reads while restricting writes to admin users."""
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return [IsStaffOrAdmin()]

    def list(self, request, *args, **kwargs):
        """Cache the event list response for a short period."""
        cached_data = cache.get(EVENT_LIST_CACHE_KEY)
        if cached_data is not None:
            return response.Response(cached_data)

        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        cache.set(EVENT_LIST_CACHE_KEY, serializer.data, EVENT_LIST_CACHE_TIMEOUT)
        return response.Response(serializer.data)

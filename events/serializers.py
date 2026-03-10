"""Serializers for event APIs."""
from rest_framework import serializers

from events.models import Event


class EventSerializer(serializers.ModelSerializer):
    """Serializer for event records."""

    class Meta:
        model = Event
        fields = ("id", "title", "description", "date", "available_slots")

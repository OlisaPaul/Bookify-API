"""API tests for the booking system."""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from bookings.models import Booking
from events.models import Event


class BookingApiTests(APITestCase):
    """Tests for event and booking API behavior."""

    def setUp(self):
        """Create a user and an event for API tests."""
        self.user = User.objects.create_user(
            username="tester",
            password="password123",
        )
        self.other_user = User.objects.create_user(
            username="other-user",
            password="password123",
        )
        self.event = Event.objects.create(
            title="Book Launch",
            description="Launch event for the latest release.",
            date="2026-05-01T10:00:00Z",
            available_slots=20,
        )

    def test_list_events(self):
        """Users can list events."""
        response = self.client.get(reverse("event-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], self.event.title)

    def test_create_booking_for_authenticated_user(self):
        """Authenticated users can create bookings for events."""
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("booking-list"),
            {"event": self.event.id, "status": Booking.STATUS_PENDING},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(Booking.objects.get().user, self.user)

    def test_user_cannot_book_same_event_twice(self):
        """Duplicate bookings for the same user and event are rejected."""
        Booking.objects.create(user=self.user, event=self.event)
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("booking-list"),
            {"event": self.event.id, "status": Booking.STATUS_CONFIRMED},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["event"][0], "You have already booked this event.")

    def test_list_bookings_only_returns_current_users_bookings(self):
        """Booking list only includes bookings owned by the authenticated user."""
        user_booking = Booking.objects.create(user=self.user, event=self.event)
        other_event = Event.objects.create(
            title="Author Meetup",
            description="Meet the author.",
            date="2026-06-01T14:00:00Z",
            available_slots=15,
        )
        Booking.objects.create(user=self.other_user, event=other_event)
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("booking-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], user_booking.id)

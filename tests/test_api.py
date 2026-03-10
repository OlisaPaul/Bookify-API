"""API tests for the booking system."""
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.serializers import ValidationError
from rest_framework.test import APITestCase

from accounts.models import User
from bookings.models import Booking
from bookings.tasks import process_payment, send_booking_confirmation
from bookings.views import BookingViewSet
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
        self.event.refresh_from_db()
        self.assertEqual(self.event.available_slots, 19)

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

    def test_create_booking_fails_when_event_has_no_slots(self):
        """Booking creation is rejected when the event is sold out."""
        self.event.available_slots = 0
        self.event.save(update_fields=["available_slots"])
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("booking-list"),
            {"event": self.event.id, "status": Booking.STATUS_PENDING},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(str(response.data["event"]), "No slots available for this event.")
        self.assertEqual(Booking.objects.count(), 0)

    @patch("bookings.views.transaction.atomic")
    @patch("bookings.views.Event.objects.select_for_update")
    def test_perform_create_uses_atomic_transaction_and_row_lock(
        self,
        mock_select_for_update,
        mock_atomic,
    ):
        """The booking write path locks the event inside an atomic block."""
        mock_atomic.return_value.__enter__.return_value = None
        mock_atomic.return_value.__exit__.return_value = None

        locked_event = Event.objects.create(
            title="Locked Event",
            description="Used for transaction checks.",
            date="2026-07-01T09:00:00Z",
            available_slots=2,
        )
        locked_event.save = MagicMock()
        mock_select_for_update.return_value.get.return_value = locked_event

        serializer = MagicMock()
        serializer.validated_data = {"event": locked_event}

        view = BookingViewSet()
        view.request = MagicMock(user=self.user)

        view.perform_create(serializer)

        mock_atomic.assert_called_once()
        mock_select_for_update.assert_called_once_with()
        mock_select_for_update.return_value.get.assert_called_once_with(pk=locked_event.pk)
        locked_event.save.assert_called_once_with(update_fields=["available_slots"])
        serializer.save.assert_called_once_with(user=self.user, event=locked_event)
        self.assertEqual(locked_event.available_slots, 1)

    @patch("bookings.views.Event.objects.select_for_update")
    def test_perform_create_raises_validation_error_when_no_slots_remain(
        self,
        mock_select_for_update,
    ):
        """The locked event check prevents bookings when slots are exhausted."""
        sold_out_event = Event.objects.create(
            title="Sold Out Event",
            description="No remaining seats.",
            date="2026-08-01T09:00:00Z",
            available_slots=0,
        )
        mock_select_for_update.return_value.get.return_value = sold_out_event

        serializer = MagicMock()
        serializer.validated_data = {"event": sold_out_event}

        view = BookingViewSet()
        view.request = MagicMock(user=self.user)

        with self.assertRaises(ValidationError) as exc:
            view.perform_create(serializer)

        self.assertEqual(
            str(exc.exception.detail["event"]),
            "No slots available for this event.",
        )
        serializer.save.assert_not_called()


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "events-cache-tests",
        }
    }
)
class EventCachingTests(APITestCase):
    """Tests for event list caching and invalidation."""

    def setUp(self):
        """Create an event and start each test with an empty cache."""
        cache.clear()
        self.event = Event.objects.create(
            title="Poetry Night",
            description="An evening of readings.",
            date="2026-09-01T18:00:00Z",
            available_slots=30,
        )

    def test_event_list_returns_cached_response(self):
        """The list endpoint returns cached data within the cache window."""
        first_response = self.client.get(reverse("event-list"))
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(first_response.data[0]["title"], "Poetry Night")

        # Bypass model signals to confirm the second response is served from cache.
        Event.objects.filter(pk=self.event.pk).update(title="Updated in Database")

        second_response = self.client.get(reverse("event-list"))

        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.data[0]["title"], "Poetry Night")

    def test_event_list_cache_is_invalidated_after_event_update(self):
        """Saving an event clears the cached list response."""
        first_response = self.client.get(reverse("event-list"))
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(first_response.data[0]["title"], "Poetry Night")

        self.event.title = "Updated Poetry Night"
        self.event.save(update_fields=["title"])

        second_response = self.client.get(reverse("event-list"))

        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.data[0]["title"], "Updated Poetry Night")


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "booking-throttle-tests",
        }
    }
)
class BookingThrottleTests(APITestCase):
    """Tests for booking creation throttling."""

    def setUp(self):
        """Create an authenticated user for throttle checks."""
        cache.clear()
        self.user = User.objects.create_user(
            username="throttle-user",
            password="password123",
        )
        self.client.force_authenticate(user=self.user)

    def test_user_can_create_up_to_five_bookings_per_minute(self):
        """Five booking create requests are allowed within a minute."""
        for index in range(5):
            event = Event.objects.create(
                title=f"Event {index}",
                description="Rate-limit test event.",
                date=f"2026-10-{index + 1:02d}T10:00:00Z",
                available_slots=5,
            )
            response = self.client.post(
                reverse("booking-list"),
                {"event": event.id, "status": Booking.STATUS_PENDING},
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(Booking.objects.count(), 5)

    def test_sixth_booking_attempt_is_throttled(self):
        """The sixth booking create request in a minute returns HTTP 429."""
        for index in range(6):
            event = Event.objects.create(
                title=f"Throttle Event {index}",
                description="Rate-limit test event.",
                date=f"2026-11-{index + 1:02d}T10:00:00Z",
                available_slots=5,
            )
            response = self.client.post(
                reverse("booking-list"),
                {"event": event.id, "status": Booking.STATUS_PENDING},
            )

            if index < 5:
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            else:
                self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class BookingTaskWorkflowTests(TestCase):
    """Tests for the Celery-driven booking workflow."""

    def setUp(self):
        """Create a booking that tasks can operate on deterministically."""
        self.user = User.objects.create_user(
            username="task-user",
            password="password123",
        )
        self.event = Event.objects.create(
            title="Async Event",
            description="Used for Celery workflow tests.",
            date="2026-12-01T10:00:00Z",
            available_slots=10,
        )
        self.booking = Booking.objects.create(
            user=self.user,
            event=self.event,
            status=Booking.STATUS_PENDING,
        )

    def test_successful_payment_flow_marks_booking_paid_then_confirmed(self):
        """Successful payment processing marks a booking paid before confirmation."""
        original_confirmation_run = send_booking_confirmation.run

        def confirmation_side_effect(booking_id):
            self.booking.refresh_from_db()
            self.assertEqual(self.booking.status, Booking.STATUS_PAID)
            return original_confirmation_run(booking_id)

        self.assertEqual(self.booking.status, Booking.STATUS_PENDING)

        with patch(
            "bookings.tasks.send_booking_confirmation.delay",
            side_effect=confirmation_side_effect,
        ) as mock_confirmation_delay:
            process_payment.run(self.booking.id)

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.STATUS_CONFIRMED)
        mock_confirmation_delay.assert_called_once_with(self.booking.id)

    @patch("bookings.tasks.payment_succeeds", return_value=False)
    @patch("bookings.tasks.send_booking_confirmation.delay")
    def test_payment_failure_flow_marks_booking_failed(
        self,
        mock_confirmation_delay,
        mock_payment_succeeds,
    ):
        """Failed payment processing marks the booking as failed and stops confirmation."""
        self.assertEqual(self.booking.status, Booking.STATUS_PENDING)

        process_payment.run(self.booking.id)

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.STATUS_FAILED)
        mock_payment_succeeds.assert_called_once_with()
        mock_confirmation_delay.assert_not_called()

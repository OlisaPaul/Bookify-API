"""Root URL configuration for the Bookify API."""
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from bookings.views import BookingViewSet
from events.views import EventViewSet


router = DefaultRouter()
router.register("events", EventViewSet, basename="event")
router.register("bookings", BookingViewSet, basename="booking")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
]

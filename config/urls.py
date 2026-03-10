"""Root URL configuration for the Bookify API."""
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from bookings.views import BookingViewSet
from events.views import EventViewSet


router = DefaultRouter()
router.register("events", EventViewSet, basename="event")
router.register("bookings", BookingViewSet, basename="booking")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include(router.urls)),
]

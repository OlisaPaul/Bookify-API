"""Models for the accounts app."""
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Custom user model for the booking system."""

    pass

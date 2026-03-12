"""Models for the accounts app."""
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models


class UserManager(DjangoUserManager):
    """Custom manager that keeps role and Django admin flags in sync."""

    def create_user(self, username, email=None, password=None, **extra_fields):
        """Create a user with a sensible default role."""
        role = extra_fields.setdefault("role", self.model.ROLE_CUSTOMER)
        if role in (self.model.ROLE_STAFF, self.model.ROLE_ADMIN):
            extra_fields.setdefault("is_staff", True)
        return super().create_user(username, email=email, password=password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        """Create a superuser with the admin role."""
        extra_fields.setdefault("role", self.model.ROLE_ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return super().create_superuser(username, email=email, password=password, **extra_fields)


class User(AbstractUser):
    """Custom user model for the booking system."""

    ROLE_CUSTOMER = "customer"
    ROLE_STAFF = "staff"
    ROLE_ADMIN = "admin"

    ROLE_CHOICES = (
        (ROLE_CUSTOMER, "Customer"),
        (ROLE_STAFF, "Staff"),
        (ROLE_ADMIN, "Admin"),
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_CUSTOMER,
    )

    objects = UserManager()

    def save(self, *args, **kwargs):
        """Keep Django admin flags aligned with privileged roles."""
        if self.is_superuser:
            self.role = self.ROLE_ADMIN

        if self.role in (self.ROLE_STAFF, self.ROLE_ADMIN):
            self.is_staff = True

        super().save(*args, **kwargs)

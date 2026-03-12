"""Custom permission classes for role-based access control."""
from rest_framework.permissions import BasePermission

from accounts.models import User


class IsAdmin(BasePermission):
    """Allow access only to admin users."""

    def has_permission(self, request, view):
        """Return True when the user has the admin role."""
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or user.role == User.ROLE_ADMIN)
        )


class IsStaffOrAdmin(BasePermission):
    """Allow access to staff and admin users."""

    def has_permission(self, request, view):
        """Return True when the user has a privileged role."""
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or user.role in (User.ROLE_STAFF, User.ROLE_ADMIN)
            )
        )


class IsCustomer(BasePermission):
    """Allow access only to customer users."""

    def has_permission(self, request, view):
        """Return True when the user has the customer role."""
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.role == User.ROLE_CUSTOMER
        )

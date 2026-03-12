"""Admin configuration for account models."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Admin configuration for custom users."""

    fieldsets = UserAdmin.fieldsets + (
        ("Role", {"fields": ("role",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Role", {"fields": ("role",)}),
    )
    list_display = ("username", "email", "role", "is_staff", "is_active")

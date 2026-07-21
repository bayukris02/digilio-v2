from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """Full access for admin users only."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff


class IsAuthenticatedReadOnly(permissions.BasePermission):
    """Any authenticated user can read; only staff can write."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff

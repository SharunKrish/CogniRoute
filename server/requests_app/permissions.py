from rest_framework import permissions

class IsAdminUserRole(permissions.BasePermission):
    """
    Custom permission to only allow access to users with the 'admin' role.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            getattr(request.user, 'role', '') == 'admin'
        )

class IsAgentUserRole(permissions.BasePermission):
    """
    Custom permission to only allow access to users with the 'agent' or 'admin' role.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            getattr(request.user, 'role', '') in ['admin', 'agent']
        )

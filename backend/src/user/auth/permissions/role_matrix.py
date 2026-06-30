from src.user.auth.permissions.enum import Permission
from src.user.enums import UserRole

ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    # Admin - full system access for user-related functions
    UserRole.ADMIN: {
        # Dashboard permissions
        Permission.VIEW_DASHBOARD,
        Permission.EDIT_DASHBOARD,
        # User profile permissions
        Permission.VIEW_PROFILE,
        Permission.EDIT_PROFILE,
        # User management permissions
        Permission.VIEW_USERS,
        Permission.CREATE_USER,
        Permission.EDIT_USER,
        Permission.DELETE_USER,
        # Settings permissions
        Permission.VIEW_SETTINGS,
        Permission.EDIT_SETTINGS,
        # System permissions
        Permission.VIEW_LOGS,
        Permission.MANAGE_BACKUPS,
    },
    # Editor - can create and edit content but cannot manage users or system settings
    UserRole.MODERATOR: {
        # Dashboard
        Permission.VIEW_DASHBOARD,
        # Profile
        Permission.VIEW_PROFILE,
        Permission.EDIT_PROFILE,
        # Settings
        Permission.VIEW_SETTINGS,
    },
    # Viewer - read-only access to authorized resources
    UserRole.USER: {
        Permission.VIEW_PROFILE,
    },
}

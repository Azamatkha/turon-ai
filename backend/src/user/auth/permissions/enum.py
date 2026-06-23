from enum import StrEnum


class Permission(StrEnum):
    # Dashboard permissions
    VIEW_DASHBOARD = "view_dashboard"
    EDIT_DASHBOARD = "edit_dashboard"

    # User profile permissions
    VIEW_PROFILE = "view_profile"
    EDIT_PROFILE = "edit_profile"

    # User management permissions
    VIEW_USERS = "view_users"
    CREATE_USER = "create_user"
    EDIT_USER = "edit_user"
    DELETE_USER = "delete_user"

    # Settings permissions
    VIEW_SETTINGS = "view_settings"
    EDIT_SETTINGS = "edit_settings"

    # System permissions
    VIEW_LOGS = "view_logs"
    MANAGE_BACKUPS = "manage_backups"

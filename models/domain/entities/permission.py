from enum import Enum


class Permission(str, Enum):
    MANAGE_OWN_ACCOUNT = "account.manage.own"
    VIEW_ADMIN_DASHBOARD = "admin.dashboard.view"
    VIEW_ADMIN_AUDIT = "admin.audit.view"
    MANAGE_USERS = "users.manage"
    VIEW_PERMISSIONS = "permissions.view"
    MANAGE_FLOOR_PLAN = "floor_plan.manage"
    EDIT_INSTITUTION_SETTINGS = "institution.settings.edit"

    VIEW_MANAGER_DASHBOARD = "manager.dashboard.view"
    REVIEW_RESERVATIONS = "reservations.review"
    MANAGE_SPACES = "spaces.manage"
    RESOLVE_CONFLICTS = "conflicts.resolve"

    VIEW_REQUESTER_DASHBOARD = "requester.dashboard.view"
    CREATE_RESERVATION = "reservations.create"
    CANCEL_OWN_RESERVATION = "reservations.cancel.own"
    VIEW_AGENDA = "agenda.view"
    VIEW_NOTIFICATIONS = "notifications.view"

    VIEW_PARTICIPANT_DASHBOARD = "participant.dashboard.view"
    LOCATE_SPACES = "spaces.locate"

import unittest

from models.domain.entities.institution import Institution
from models.domain.entities.permission import Permission
from models.domain.entities.profile import Profile
from models.domain.entities.user import User, UserStatus
from models.domain.exceptions import InstitutionAccessDenied, PermissionDenied
from models.domain.policies.permission_policy import PermissionPolicy


class UserPermissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.admin = User(
            id="admin-1",
            name="Admin institucional",
            email="admin@example.test",
            profile=Profile.ADMIN,
            institution_id="institution-a",
        )
        self.permission_policy = PermissionPolicy()

    def test_admin_can_list_and_manage_within_linked_institution(self) -> None:
        scope = self.permission_policy.authorize_listing(
            self.admin,
            Permission.MANAGE_USERS,
        )

        self.permission_policy.authorize_resource(
            self.admin,
            Permission.MANAGE_USERS,
            Institution("institution-a", "Instituição A"),
        )

        self.assertEqual(scope, "institution-a")

    def test_request_cannot_change_admin_listing_scope(self) -> None:
        with self.assertRaises(InstitutionAccessDenied):
            self.permission_policy.authorize_listing(
                self.admin,
                Permission.MANAGE_USERS,
                requested_institution_id="institution-b",
            )

    def test_admin_cannot_read_or_change_resource_from_another_institution(self) -> None:
        with self.assertRaises(InstitutionAccessDenied):
            self.permission_policy.authorize_resource(
                self.admin,
                Permission.MANAGE_USERS,
                Institution("institution-b", "Instituição B"),
            )

    def test_admin_must_have_an_institution_link(self) -> None:
        with self.assertRaises(ValueError):
            User(
                id="unlinked-admin",
                name="Admin sem vínculo",
                email="unlinked@example.test",
                profile=Profile.ADMIN,
                institution_id=None,
            )

    def test_requester_and_participant_have_personal_notification_permissions(self) -> None:
        self.assertEqual(self.permission_policy.effective_permissions(Profile.REQUESTER), frozenset({
            Permission.MANAGE_OWN_ACCOUNT, Permission.CREATE_RESERVATION,
            Permission.VIEW_OWN_RESERVATIONS, Permission.CANCEL_OWN_RESERVATION, Permission.VIEW_NOTIFICATIONS,
        }))
        self.assertEqual(
            self.permission_policy.effective_permissions(Profile.PARTICIPANT),
            frozenset({Permission.MANAGE_OWN_ACCOUNT, Permission.VIEW_NOTIFICATIONS}),
        )

    def test_manager_can_manage_rooms_but_not_institution_structure(self) -> None:
        grants = self.permission_policy.effective_permissions(Profile.MANAGER)
        self.assertIn(Permission.MANAGE_SPACES, grants)
        self.assertNotIn(Permission.MANAGE_FLOOR_PLAN, grants)

        requester = User(
            id="requester-1",
            name="Solicitante",
            email="requester@example.test",
            profile=Profile.REQUESTER,
            institution_id="institution-a",
        )
        with self.assertRaises(PermissionDenied):
            self.permission_policy.authorize_listing(
                requester,
                Permission.VIEW_AGENDA,
            )

    def test_every_profile_can_manage_only_its_own_account(self) -> None:
        for profile in Profile:
            with self.subTest(profile=profile):
                user = User(
                    id=f"{profile.value}-1",
                    name="Pessoa RoomFlow",
                    email="person@example.test",
                    profile=profile,
                    institution_id="institution-a",
                )
                self.permission_policy.authorize_own_account(user, user.id)
                with self.assertRaises(PermissionDenied):
                    self.permission_policy.authorize_own_account(user, "other-user")

    def test_inactive_admin_cannot_use_an_institutional_grant(self) -> None:
        inactive_admin = User(
            id="admin-inactive",
            name="Admin inativo",
            email="inactive@example.test",
            profile=Profile.ADMIN,
            institution_id="institution-a",
            status=UserStatus.INACTIVE,
        )

        with self.assertRaises(PermissionDenied):
            self.permission_policy.authorize_listing(
                inactive_admin,
                Permission.MANAGE_USERS,
            )


if __name__ == "__main__":
    unittest.main()

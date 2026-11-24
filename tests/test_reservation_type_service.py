
import unittest

from application.services.reservation_type_service import ReservationTypeService
from models.domain.entities.profile import Profile
from models.domain.entities.user import User, UserStatus
from models.domain.entities.reservation_type import ReservationType
from models.domain.exceptions import PermissionDenied, ResourceNotFound


class FakeReservationTypeRepository:
    def __init__(self):
        self.types = {}

    def list_types(self, institution_id, include_inactive=False):
        result = [
            item for item in self.types.values()
            if item.institution_id == institution_id
        ]

        if not include_inactive:
            result = [item for item in result if item.active]

        return result

    def find_type(self, type_id):
        return self.types.get(type_id)

    def add_type(self, reservation_type):
        self.types[reservation_type.id] = reservation_type
        return reservation_type

    def save_type(self, reservation_type):
        self.types[reservation_type.id] = reservation_type


class ReservationTypeServiceTests(unittest.TestCase):

    def setUp(self):
        self.repository = FakeReservationTypeRepository()
        self.service = ReservationTypeService(self.repository)

        self.admin = User(
            id="1",
            name="Administrador",
            email="admin@email.com",
            profile=Profile.ADMIN,
            institution_id="10",
        )

        self.manager = User(
            id="2",
            name="Gerente",
            email="gerente@email.com",
            profile=Profile.MANAGER,
            institution_id="10",
        )

        self.participant = User(
            id="3",
            name="Participante",
            email="participante@email.com",
            profile=Profile.PARTICIPANT,
            institution_id="10",
        )

        self.inactive_admin = User(
            id="4",
            name="Administrador inativo",
            email="inativo@email.com",
            profile=Profile.ADMIN,
            institution_id="10",
            status=UserStatus.INACTIVE,
        )

        self.repository.add_type(
            ReservationType(
                id="rt-1",
                institution_id="10",
                name="Palestra",
            )
        )

        self.repository.add_type(
            ReservationType(
                id="rt-2",
                institution_id="20",
                name="Reunião",
            )
        )

    def test_admin_can_list_reservation_types(self):
        result = self.service.list_types(self.admin)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "Palestra")

    def test_manager_can_list_reservation_types(self):
        result = self.service.list_types(self.manager)

        self.assertEqual(len(result), 1)

    def test_participant_cannot_list_reservation_types(self):
        with self.assertRaises(PermissionDenied):
            self.service.list_types(self.participant)

    def test_inactive_user_cannot_list_reservation_types(self):
        with self.assertRaises(PermissionDenied):
            self.service.list_types(self.inactive_admin)

    def test_get_type_from_same_institution(self):
        result = self.service.get_type(self.admin, "rt-1")

        self.assertEqual(result.name, "Palestra")

    def test_cannot_access_type_from_another_institution(self):
        with self.assertRaises(ResourceNotFound):
            self.service.get_type(self.admin, "rt-2")

    def test_create_type_normalizes_name(self):
        result = self.service.create_type(
            self.admin,
            "  Aula   Especial  ",
            "  Atividade acadêmica  ",
        )

        self.assertEqual(result.name, "Aula Especial")
        self.assertEqual(result.description, "Atividade acadêmica")
        self.assertEqual(result.institution_id, "10")

    def test_update_type(self):
        result = self.service.update_type(
            self.admin,
            "rt-1",
            "Workshop",
            "Atividade prática",
        )

        self.assertEqual(result.name, "Workshop")
        self.assertEqual(result.description, "Atividade prática")

    def test_deactivate_type(self):
        result = self.service.set_type_active(
            self.admin,
            "rt-1",
            False,
        )

        self.assertFalse(result.active)

    def test_activate_type(self):
        self.service.set_type_active(self.admin, "rt-1", False)

        result = self.service.set_type_active(
            self.admin,
            "rt-1",
            True,
        )

        self.assertTrue(result.active)

    def test_inactive_type_is_not_listed_by_default(self):
        self.service.set_type_active(self.admin, "rt-1", False)

        result = self.service.list_types(self.admin)

        self.assertEqual(len(result), 0)

    def test_inactive_type_can_be_listed_when_requested(self):
        self.service.set_type_active(self.admin, "rt-1", False)

        result = self.service.list_types(
            self.admin,
            include_inactive=True,
        )

        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()


import unittest
from dataclasses import replace

from infrastructure.repositories.in_memory_reservation_type_repository import (
    InMemoryReservationTypeRepository,
)
from models.domain.entities.reservation_type import ReservationType
from models.domain.exceptions import DuplicateResource, ResourceNotFound


class InMemoryReservationTypeRepositoryTests(unittest.TestCase):

    def setUp(self):
        self.repository = InMemoryReservationTypeRepository()

    def make_type(
        self,
        type_id="1",
        institution_id="inst-1",
        name="Palestra",
        active=True,
    ):
        return ReservationType(
            id=type_id,
            institution_id=institution_id,
            name=name,
            active=active,
        )

    def test_add_and_find_type(self):
        item = self.make_type()
        self.repository.add_type(item)

        self.assertEqual(self.repository.find_type("1"), item)

    def test_reject_duplicate_id(self):
        self.repository.add_type(self.make_type())

        with self.assertRaises(DuplicateResource):
            self.repository.add_type(
                self.make_type(name="Reunião")
            )

    def test_reject_duplicate_name_case_insensitive(self):
        self.repository.add_type(self.make_type())

        with self.assertRaises(DuplicateResource):
            self.repository.add_type(
                self.make_type(
                    type_id="2",
                    name="PALESTRA",
                )
            )

    def test_allow_same_name_in_different_institutions(self):
        self.repository.add_type(self.make_type())

        other = self.make_type(
            type_id="2",
            institution_id="inst-2",
        )

        self.repository.add_type(other)

        self.assertEqual(len(self.repository.list_types("inst-2")), 1)

    def test_list_only_institution_types(self):
        self.repository.add_type(self.make_type())
        self.repository.add_type(
            self.make_type(type_id="2", institution_id="inst-2")
        )

        result = self.repository.list_types("inst-1")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].institution_id, "inst-1")

    def test_filter_inactive_types(self):
        self.repository.add_type(self.make_type())
        self.repository.add_type(
            self.make_type(
                type_id="2",
                name="Reunião",
                active=False,
            )
        )

        self.assertEqual(len(self.repository.list_types("inst-1")), 1)
        self.assertEqual(
            len(self.repository.list_types("inst-1", include_inactive=True)),
            2,
        )

    def test_save_type(self):
        original = self.make_type()
        self.repository.add_type(original)

        updated = replace(original, name="Seminário")
        self.repository.save_type(updated)

        self.assertEqual(
            self.repository.find_type("1").name,
            "Seminário",
        )

    def test_reject_update_with_duplicate_name(self):
        self.repository.add_type(self.make_type())
        self.repository.add_type(
            self.make_type(type_id="2", name="Reunião")
        )

        updated = self.make_type(type_id="2", name="PALESTRA")

        with self.assertRaises(DuplicateResource):
            self.repository.save_type(updated)

    def test_reject_update_from_another_institution(self):
        original = self.make_type()
        self.repository.add_type(original)

        changed = replace(original, institution_id="inst-2")

        with self.assertRaises(ValueError):
            self.repository.save_type(changed)

    def test_reject_update_of_missing_type(self):
        with self.assertRaises(ResourceNotFound):
            self.repository.save_type(self.make_type())

    def test_sort_types_by_name(self):
        self.repository.add_type(self.make_type(name="Zoologia"))
        self.repository.add_type(
            self.make_type(type_id="2", name="Auditório")
        )

        result = self.repository.list_types("inst-1")

        self.assertEqual(
            [item.name for item in result],
            ["Auditório", "Zoologia"],
        )


if __name__ == "__main__":
    unittest.main()

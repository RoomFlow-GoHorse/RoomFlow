
import unittest

from models.domain.entities.reservation_type import ReservationType


class ReservationTypeTests(unittest.TestCase):

    def test_create_valid_reservation_type(self):
        item = ReservationType("1", "10", "Palestra")

        self.assertEqual(item.name, "Palestra")
        self.assertTrue(item.active)

    def test_reject_empty_name(self):
        with self.assertRaises(ValueError):
            ReservationType("1", "10", "")

    def test_reject_name_over_100_characters(self):
        with self.assertRaises(ValueError):
            ReservationType("1", "10", "A" * 101)

    def test_reject_empty_id(self):
        with self.assertRaises(ValueError):
            ReservationType("", "10", "Palestra")

    def test_reject_empty_institution_id(self):
        with self.assertRaises(ValueError):
            ReservationType("1", "", "Palestra")

    def test_reject_description_over_255_characters(self):
        with self.assertRaises(ValueError):
            ReservationType("1", "10", "Palestra", "A" * 256)


if __name__ == "__main__":
    unittest.main()

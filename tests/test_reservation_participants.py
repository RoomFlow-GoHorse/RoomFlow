from datetime import datetime, timezone
import unittest

from controllers.http.reservations import ReservationPayload
from models.domain.entities.reservation import ReservationRequest


class ReservationParticipantPayloadTests(unittest.TestCase):
    def _payload(self, participant_ids=None):
        data = {
            "space_id": "space-1",
            "title": "Reunião de projeto",
            "activity_type": "Reunião",
            "start": datetime(2027, 1, 10, 13, tzinfo=timezone.utc),
            "end": datetime(2027, 1, 10, 14, tzinfo=timezone.utc),
            "participants": 2,
        }
        if participant_ids is not None:
            data["participant_ids"] = participant_ids
        return ReservationPayload(**data)

    def test_omitted_participants_remain_unspecified_for_an_edit(self):
        self.assertIsNone(self._payload().to_request().participant_ids)

    def test_explicit_empty_participants_can_remove_existing_links(self):
        self.assertEqual(self._payload([]).to_request().participant_ids, frozenset())

    def test_rejects_duplicate_participants(self):
        with self.assertRaises(ValueError):
            self._payload(["participant-1", "participant-1"]).to_request()

    def test_rejects_more_links_than_expected_people(self):
        request = self._payload(["participant-1", "participant-2", "participant-3"]).to_request()
        with self.assertRaises(ValueError):
            request.validated()


if __name__ == "__main__":
    unittest.main()

from urllib.parse import quote


class ApiReservations:
    def __init__(self, api):
        self._api = api

    def catalog(self, start=None, end=None):
        params = {"start": start.isoformat(), "end": end.isoformat()} if start is not None and end is not None else None
        return self._api.request("GET", "/reservations/spaces", params=params)

    def eligible_participants(self):
        return self._api.request("GET", "/reservations/participants")

    def create(self, payload):
        return self._api.request("POST", "/reservations", payload=payload)

    def list_own(self):
        return self._api.request("GET", "/reservations/mine")

    def list_institution(self):
        return self._api.request("GET", "/reservations/institution")

    def list_participating(self):
        return self._api.request("GET", "/reservations/participating")

    def participating_detail(self, reservation_id):
        return self._api.request("GET", f"/reservations/participating/{quote(reservation_id, safe='')}")

    def respond_participation(self, reservation_id, status):
        return self._api.request(
            "PATCH", f"/reservations/participating/{quote(reservation_id, safe='')}", payload={"status": status},
        )

    def detail(self, reservation_id):
        return self._api.request("GET", f"/reservations/{quote(reservation_id, safe='')}")

    def detail_own(self, reservation_id):
        return self._api.request("GET", f"/reservations/mine/{quote(reservation_id, safe='')}")

    def edit(self, reservation_id, payload):
        return self._api.request("PUT", f"/reservations/{quote(reservation_id, safe='')}", payload=payload)

    def cancel(self, reservation_id, reason=None):
        return self._api.request(
            "POST", f"/reservations/{quote(reservation_id, safe='')}/cancel", payload={"reason": reason},
        )

    def review(self, reservation_id, status, reason=None):
        return self._api.request(
            "PATCH", f"/reservations/{quote(reservation_id, safe='')}/decision",
            payload={"status": status, "reason": reason},
        )

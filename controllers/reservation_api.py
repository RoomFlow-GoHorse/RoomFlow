from urllib.parse import quote


class ApiReservations:
    def __init__(self, api):
        self._api = api

    def catalog(self, start=None, end=None):
        params = {"start": start.isoformat(), "end": end.isoformat()} if start is not None and end is not None else None
        return self._api.request("GET", "/reservations/spaces", params=params)

    def create(self, payload):
        return self._api.request("POST", "/reservations", payload=payload)

    def list_own(self):
        return self._api.request("GET", "/reservations/mine")

    def list_institution(self):
        return self._api.request("GET", "/reservations/institution")

    def edit(self, reservation_id, payload):
        return self._api.request("PUT", f"/reservations/{quote(reservation_id, safe='')}", payload=payload)

    def cancel(self, reservation_id):
        return self._api.request("POST", f"/reservations/{quote(reservation_id, safe='')}/cancel")

    def review(self, reservation_id, status, reason=None):
        return self._api.request(
            "PATCH", f"/reservations/{quote(reservation_id, safe='')}/decision",
            payload={"status": status, "reason": reason},
        )

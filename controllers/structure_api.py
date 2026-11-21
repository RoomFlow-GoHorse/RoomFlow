from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from urllib.parse import quote

from application.read_models.admin_dashboard import AdminDashboardMetrics, EntityCounts, ProfileCount, RecentUser
from models.domain.entities.building import Building
from models.domain.entities.floor import Floor
from models.domain.entities.floor_plan import RoomPosition
from models.domain.entities.profile import Profile
from models.domain.entities.resource import Resource
from models.domain.entities.space import Space
from models.domain.exceptions import ResourceNotFound


def _id(value: str) -> str:
    return quote(value, safe="")


def _space(data):
    return Space(**{
        **data,
        "resources": tuple(data["resources"]),
        "resource_ids": tuple(data["resource_ids"]),
        "resource_quantities": tuple(data["resource_quantities"].items()),
    })


class ApiSpaceManagement:
    def __init__(self, api):
        self._api = api

    def list_buildings(self, actor, include_inactive=False):
        data = self._api.request("GET", "/structure/buildings", params={"include_inactive": include_inactive})
        return [Building(**item) for item in data]

    def create_building(self, actor, name):
        return Building(**self._api.request("POST", "/structure/buildings", payload={"name": name}))

    def update_building(self, actor, building_id, name):
        return Building(**self._api.request("PATCH", f"/structure/buildings/{_id(building_id)}", payload={"name": name}))

    def deactivate_building(self, actor, building_id):
        return self._building_status(building_id, False)

    def activate_building(self, actor, building_id):
        return self._building_status(building_id, True)

    def _building_status(self, building_id, active):
        return Building(**self._api.request("PATCH", f"/structure/buildings/{_id(building_id)}/status",
                                           payload={"active": active}))

    def list_floors(self, actor, building_id, include_inactive=False):
        data = self._api.request("GET", f"/structure/buildings/{_id(building_id)}/floors",
                                 params={"include_inactive": include_inactive})
        return [Floor(**item) for item in data]

    def create_floor(self, actor, building_id, name):
        return Floor(**self._api.request("POST", f"/structure/buildings/{_id(building_id)}/floors",
                                         payload={"name": name}))

    def update_floor(self, actor, floor_id, name):
        return Floor(**self._api.request("PATCH", f"/structure/floors/{_id(floor_id)}", payload={"name": name}))

    def deactivate_floor(self, actor, floor_id):
        return self._floor_status(floor_id, False)

    def activate_floor(self, actor, floor_id):
        return self._floor_status(floor_id, True)

    def _floor_status(self, floor_id, active):
        return Floor(**self._api.request("PATCH", f"/structure/floors/{_id(floor_id)}/status",
                                        payload={"active": active}))

    def list_spaces(self, actor, search="", status=None, building_id=None, floor_id=None,
                    resource_id=None, include_inactive=False):
        filters = dict(q=search, status=status, building_id=building_id, floor_id=floor_id,
                       resource_id=resource_id, include_inactive=include_inactive)
        params = {key: value for key, value in filters.items() if value is not None}
        return [_space(item) for item in self._api.request("GET", "/structure/spaces", params=params)]

    def get_space(self, actor, space_id):
        return _space(self._api.request("GET", f"/structure/spaces/{_id(space_id)}"))

    def create_space(self, actor, floor_id, name, room_type, capacity, status="disponivel"):
        return _space(self._api.request("POST", "/structure/spaces", payload={
            "floor_id": floor_id, "name": name, "type": room_type, "capacity": capacity, "status": status,
        }))

    def update_space(self, actor, space_id, name=None, room_type=None, capacity=None, status=None, floor_id=None):
        return _space(self._api.request("PATCH", f"/structure/spaces/{_id(space_id)}", payload={
            "name": name, "type": room_type, "capacity": capacity, "status": status, "floor_id": floor_id,
        }))

    def deactivate_space(self, actor, space_id):
        return self._space_status(space_id, False)

    def activate_space(self, actor, space_id):
        return self._space_status(space_id, True)

    def _space_status(self, space_id, active):
        return _space(self._api.request("PATCH", f"/structure/spaces/{_id(space_id)}/status",
                                       payload={"active": active}))


class ApiResourceManagement:
    def __init__(self, api):
        self._api = api

    def list_resources(self, actor, search="", include_inactive=False):
        data = self._api.request("GET", "/structure/resources",
                                 params={"q": search, "include_inactive": include_inactive})
        return [Resource(**item) for item in data]

    def create_resource(self, actor, name, quantity_total=0, quantity_unavailable=0):
        return Resource(**self._api.request("POST", "/structure/resources", payload={
            "name": name, "quantity_total": quantity_total, "quantity_unavailable": quantity_unavailable,
        }))

    def update_resource(self, actor, resource_id, name, quantity_total=None, quantity_unavailable=None):
        return Resource(**self._api.request("PATCH", f"/structure/resources/{_id(resource_id)}", payload={
            "name": name, "quantity_total": quantity_total, "quantity_unavailable": quantity_unavailable,
        }))

    def set_resource_active(self, actor, resource_id, active):
        return Resource(**self._api.request("PATCH", f"/structure/resources/{_id(resource_id)}/status",
                                            payload={"active": active}))

    def set_space_resources(self, actor, space_id, resource_ids, quantities=None):
        return _space(self._api.request("PUT", f"/structure/spaces/{_id(space_id)}/resources",
                                       payload={"resource_ids": resource_ids, "quantities": quantities or {}}))

    def update_space_configuration(self, space_id, capacity, resource_ids):
        return _space(self._api.request("PUT", f"/structure/spaces/{_id(space_id)}/configuration",
                                       payload={"capacity": capacity, "resource_ids": resource_ids}))


@dataclass(frozen=True, slots=True)
class ApiPlan:
    id: str
    institution_id: str
    building_id: str
    floor_id: str
    original_filename: str
    media_type: str
    checksum: str
    positions: tuple[RoomPosition, ...]


class ApiFloorPlans:
    def __init__(self, api):
        self._api = api

    @staticmethod
    def _plan(data):
        return ApiPlan(**{**data, "positions": tuple(RoomPosition(**item) for item in data["positions"])})

    def get_for_floor(self, actor, floor_id):
        try:
            return self._plan(self._api.request("GET", f"/structure/floors/{_id(floor_id)}/plan"))
        except ResourceNotFound:
            return None

    def read_file(self, actor, floor_id):
        for _ in range(2):
            plan = self.get_for_floor(actor, floor_id)
            if plan is None:
                raise ResourceNotFound("Planta não encontrada.")
            content = self._api.request("GET", f"/structure/floors/{_id(floor_id)}/plan/file", binary=True)
            if sha256(content).hexdigest() == plan.checksum:
                return plan, content
        raise ResourceNotFound("A planta foi substituída. Atualize a página.")

    def upload(self, actor, floor_id, filename, content):
        return self._plan(self._api.request("POST", f"/structure/floors/{_id(floor_id)}/plan",
                                            files={"file": (filename, content)}))

    def remove(self, actor, floor_id):
        self._api.request("DELETE", f"/structure/floors/{_id(floor_id)}/plan")

    def set_room_position(self, actor, floor_id, space_id, x, y):
        return self._plan(self._api.request("PUT", f"/structure/floors/{_id(floor_id)}/positions/{_id(space_id)}",
                                           payload={"x": x, "y": y}))

    def remove_room_position(self, actor, floor_id, space_id):
        return self._plan(self._api.request("DELETE", f"/structure/floors/{_id(floor_id)}/positions/{_id(space_id)}"))


class ApiAdminDashboard:
    def __init__(self, api):
        self._api = api

    def get_metrics(self, actor, period_days):
        data = self._api.request("GET", "/admin/dashboard", params={"period_days": period_days}, enveloped=False)
        return AdminDashboardMetrics(**{
            **data,
            **{name: EntityCounts(**data[name]) for name in ("users", "buildings", "floors", "spaces", "resources")},
            "users_by_profile": tuple(ProfileCount(Profile(item["profile"]), item["count"])
                                      for item in data["users_by_profile"]),
            "recent_users": tuple(RecentUser(**{
                **item, "profile": Profile(item["profile"]), "created_at": datetime.fromisoformat(item["created_at"]),
            }) for item in data["recent_users"]),
        })

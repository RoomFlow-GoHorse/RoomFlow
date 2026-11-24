import unittest

from fastapi.testclient import TestClient

from api.app import create_app


def _login(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


class StructureManagementApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.context = TestClient(create_app(environment="test"))
        self.client = self.context.__enter__()
        self.admin = _login(self.client, "admin@gmail.com", "admin123")
        self.manager = _login(self.client, "gerente@gmail.com", "gerente123")

    def tearDown(self) -> None:
        self.context.__exit__(None, None, None)

    def _create_structure(self):
        building = self.client.post(
            "/structure/buildings", headers=self.admin, json={"name": "Bloco de Pesquisa"}
        )
        self.assertEqual(building.status_code, 201)
        building_id = building.json()["data"]["id"]
        floor = self.client.post(
            f"/structure/buildings/{building_id}/floors",
            headers=self.admin,
            json={"name": "Térreo"},
        )
        self.assertEqual(floor.status_code, 201)
        floor_id = floor.json()["data"]["id"]
        return building_id, floor_id

    def test_manager_combines_filters_and_edits_a_room_with_its_resources(self):
        building_id, floor_id = self._create_structure()
        room = self.client.post("/structure/spaces", headers=self.admin, json={
            "floor_id": floor_id, "name": "Sala Filtro", "type": "Seminário", "capacity": 29,
        }).json()["data"]["id"]
        resource = self.client.post("/structure/resources", headers=self.manager, json={
            "name": "Câmera de teste",
        }).json()["data"]["id"]
        changed = self.client.put(f"/structure/spaces/{room}/configuration", headers=self.manager, json={
            "name": "Sala Editada", "type": "Estúdio", "capacity": 31, "resource_ids": [resource],
        })
        self.assertEqual(changed.status_code, 200, changed.text)
        filters = {
            "q": "editada", "building_id": building_id, "floor_id": floor_id, "room_type": "Estúdio",
            "min_capacity": 31, "max_capacity": 31, "resource_id": resource, "status": "disponivel",
        }
        result = self.client.get("/structure/spaces", headers=self.manager, params=filters)
        self.assertEqual([item["id"] for item in result.json()["data"]], [room])
        self.assertFalse(result.json()["data"][0]["occupancy_verified"])
        filters["max_capacity"] = 30
        self.assertEqual(self.client.get("/structure/spaces", headers=self.manager, params=filters).status_code, 422)
        for path in ("/structure/buildings", f"/structure/buildings/{building_id}/floors", "/admin/users", "/institutions/me"):
            self.assertEqual(self.client.get(path, headers=self.manager).status_code, 403, path)

    def test_building_floor_room_crud_and_relationship_updates(self):
        building_id, floor_id = self._create_structure()
        room = self.client.post(
            "/structure/spaces",
            headers=self.admin,
            json={"floor_id": floor_id, "name": "Lab 01", "type": "Laboratório", "capacity": 24},
        )
        self.assertEqual(room.status_code, 201)
        data = room.json()["data"]
        room_id = data["id"]
        self.assertEqual(data["building_id"], building_id)
        self.assertEqual(data["floor_id"], floor_id)
        self.assertEqual(self.client.get(f"/structure/buildings/{building_id}", headers=self.admin).status_code, 200)
        self.assertEqual(self.client.get(f"/structure/floors/{floor_id}", headers=self.admin).status_code, 200)
        self.assertEqual(self.client.get(f"/structure/buildings/{building_id}/floors", headers=self.admin).status_code, 200)

        updated_floor = self.client.patch(
            f"/structure/floors/{floor_id}", headers=self.admin, json={"name": "1º andar"}
        )
        updated_building = self.client.patch(
            f"/structure/buildings/{building_id}", headers=self.admin, json={"name": "Bloco Ciências"}
        )
        updated_room = self.client.patch(
            f"/structure/spaces/{room_id}", headers=self.admin,
            json={"capacity": 30, "type": "Sala de aula", "status": "bloqueado"},
        )
        reloaded = self.client.get(f"/structure/spaces/{room_id}", headers=self.admin)
        self.assertEqual(updated_floor.status_code, 200)
        self.assertEqual(updated_building.status_code, 200)
        self.assertEqual(updated_room.status_code, 200)
        self.assertEqual(reloaded.json()["data"]["building"], "Bloco Ciências")
        self.assertEqual(reloaded.json()["data"]["floor"], "1º andar")
        self.assertEqual(reloaded.json()["data"]["capacity"], 30)
        self.assertEqual(reloaded.json()["data"]["status"], "bloqueado")

    def test_duplicate_names_capacity_and_status_validation(self):
        building_id, floor_id = self._create_structure()
        duplicate_building = self.client.post(
            "/structure/buildings", headers=self.admin, json={"name": "bloco de pesquisa"}
        )
        duplicate_floor = self.client.post(
            f"/structure/buildings/{building_id}/floors",
            headers=self.admin,
            json={"name": "térreo"},
        )
        first_room = self.client.post(
            "/structure/spaces", headers=self.admin,
            json={"floor_id": floor_id, "name": "Lab 01", "type": "Laboratório", "capacity": 24},
        )
        duplicate_room = self.client.post(
            "/structure/spaces", headers=self.admin,
            json={"floor_id": floor_id, "name": "lab 01", "type": "Laboratório", "capacity": 24},
        )
        invalid_capacity = self.client.post(
            "/structure/spaces", headers=self.admin,
            json={"floor_id": floor_id, "name": "Inválida", "type": "Sala", "capacity": 0},
        )
        invalid_status = self.client.post(
            "/structure/spaces", headers=self.admin,
            json={"floor_id": floor_id, "name": "Status", "type": "Sala", "capacity": 4, "status": "fechada"},
        )
        self.assertEqual(duplicate_building.status_code, 409)
        self.assertEqual(duplicate_floor.status_code, 409)
        self.assertEqual(first_room.status_code, 201)
        self.assertEqual(duplicate_room.status_code, 409)
        self.assertEqual(invalid_capacity.status_code, 422)
        self.assertEqual(invalid_status.status_code, 422)

    def test_inactivation_preserves_linked_records_and_requires_empty_children(self):
        building_id, floor_id = self._create_structure()
        room = self.client.post(
            "/structure/spaces", headers=self.admin,
            json={"floor_id": floor_id, "name": "Sala Persistente", "type": "Sala", "capacity": 4},
        ).json()["data"]
        blocked_building = self.client.patch(
            f"/structure/buildings/{building_id}/status", headers=self.admin, json={"active": False}
        )
        blocked_floor = self.client.patch(
            f"/structure/floors/{floor_id}/status", headers=self.admin, json={"active": False}
        )
        inactive_room = self.client.patch(
            f"/structure/spaces/{room['id']}/status", headers=self.admin, json={"active": False}
        )
        inactive_floor = self.client.patch(
            f"/structure/floors/{floor_id}/status", headers=self.admin, json={"active": False}
        )
        inactive_building = self.client.patch(
            f"/structure/buildings/{building_id}/status", headers=self.admin, json={"active": False}
        )
        preserved = self.client.get(
            f"/structure/spaces/{room['id']}", headers=self.admin
        )
        self.assertEqual(blocked_building.status_code, 422)
        self.assertEqual(blocked_floor.status_code, 422)
        self.assertEqual(inactive_room.status_code, 200)
        self.assertEqual(inactive_floor.status_code, 200)
        self.assertEqual(inactive_building.status_code, 200)
        self.assertEqual(preserved.status_code, 200)
        self.assertFalse(preserved.json()["data"]["active"])
        self.assertEqual(preserved.json()["data"]["status"], "inativo")

    def test_search_filters_manager_permissions_and_institution_isolation(self):
        building_id, floor_id = self._create_structure()
        room = self.client.post(
            "/structure/spaces", headers=self.admin,
            json={"floor_id": floor_id, "name": "Sala Filtro", "type": "Sala", "capacity": 12},
        ).json()["data"]
        found = self.client.get(
            "/structure/spaces?q=filtro&building_id=" + building_id,
            headers=self.manager,
        )
        manager_update = self.client.patch(
            f"/structure/spaces/{room['id']}", headers=self.manager, json={"capacity": 15}
        )
        forbidden_buildings = self.client.get("/structure/buildings", headers=self.manager)
        other = self.client.post(
            "/institutions/signup",
            json={
                "responsible_name": "Outro Admin", "responsible_email": "other-admin@example.edu",
                "password": "senha-segura", "name": "Outra Instituição",
                "cnpj": "98.765.432/0001-10", "institution_type": "Universidade",
            },
        )
        other_headers = _login(self.client, "other-admin@example.edu", "senha-segura")
        foreign_room = self.client.get(f"/structure/spaces/{room['id']}", headers=other_headers)
        foreign_buildings = self.client.get("/structure/buildings", headers=other_headers)
        foreign_floor_request = self.client.post(
            f"/structure/buildings/{building_id}/floors",
            headers=other_headers,
            json={"name": "Andar externo"},
        )
        foreign_space_request = self.client.post(
            "/structure/spaces", headers=other_headers,
            json={"floor_id": floor_id, "name": "Sala externa", "type": "Sala", "capacity": 8},
        )
        self.assertEqual(found.status_code, 200)
        self.assertEqual([item["id"] for item in found.json()["data"]], [room["id"]])
        self.assertEqual(manager_update.status_code, 200)
        self.assertEqual(forbidden_buildings.status_code, 403)
        self.assertEqual(other.status_code, 201)
        self.assertEqual(foreign_room.status_code, 404)
        self.assertEqual(foreign_buildings.json()["data"], [])
        self.assertEqual(foreign_floor_request.status_code, 404)
        self.assertEqual(foreign_space_request.status_code, 404)


if __name__ == "__main__":
    unittest.main()
